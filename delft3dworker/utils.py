from __future__ import absolute_import
import json
import os
import re
import logging
import sys
from django.conf import settings
from django.utils import timezone
from datetime import time, datetime


def tz_now():
    """Return current timezone aware datetime with default timezone
    as defined in settings.py."""
    return timezone.make_aware(datetime.now(), timezone.get_default_timezone())


def tz_midnight(date):
    """Return timezone aware datetime from given date."""
    t = time(0, 0, 0, tzinfo=timezone.get_default_timezone())
    return datetime.combine(date, t)


def apply_default_tz(dt):
    """Return given timezone aware datetime with default timezone
    as defined in settings.py."""
    if dt is None:
        return None
    else:
        return timezone.make_aware(dt, timezone.get_default_timezone())


def version_default():
    """For backwards compatibility with migrations."""
    return {}


def derive_defaults_from_argo(argo_yaml):
    versions = {}

    try:
        versions["parameters"] = argo_yaml.get("spec", {}).get("arguments", {}).get("parameters")
        templates = argo_yaml.get("spec", {}).get("templates", [{}])
        entrypoints = [x["name"] for x in templates if "steps" in x.keys()]
        versions["entrypoints"] = entrypoints

    except AttributeError:
        logging.warning("Couldn't retrieve Argo structure in yaml.")

    return versions


def log_progress_parser(log, container_type):
    lines = log.splitlines()
    if container_type == 'delft3d':
        for line in lines[::-1]:
            parsed = delft3d_logparser(line)
            if parsed['progress'] is not None:
                return parsed['progress']
    else:  # TODO: improve method to raise error if type is unknown
        for line in lines[::-1]:
            parsed = python_logparser(line)
            if parsed['progress'] is not None:
                return parsed['progress']


def delft3d_logparser(line):
    """
    read progress information from delft3d log.
    :param line: parse log message
    :return: progress [0-1]
    """

    try:

        percentage_re = re.compile(r"""
        ^(?P<message>.*?        # capture whole string as message
        (?P<progress>[\d\.]+)%  # capture num with . delim & ending with %
        .*
        )
        """, re.VERBOSE)
        match = percentage_re.search(line)

        if match:
            match = match.groupdict()
            match["message"] = line
            if (
                "progress" in match and
                match["progress"] is not None and
                match["progress"] != ""
            ):
                match['progress'] = float(match['progress'])
            # add default log level
            match['level'] = 'INFO'
            # add state
            match['state'] = None
        else:
            match = {"message": None, "level": "INFO",
                     "state": None, "progress": None}
        return match

    except:

        e = sys.exc_info()[1]  # get error msg

        return {
            "message": "error '%s' on line '%s'" % (e.message, line),
            "level": "ERROR",
            "state": None,
            "progress": None
        }


def python_logparser(line):
    """
    :param line: parse log message
    :return: level (string), message (string),
             progress [0-1] (float)(optional),
             state, (string)(optional)
    """

    try:

        python_re = re.compile(r"""
        ^(?P<message>
            (?P<level>
                [A-Z]+\w+
            )?  # capture first capital word as log level
            .*
            (?P<state>
                [A-Z]+\w+
            )?  # capture second capital word as log state
            .*
            (
                (?P<progress>
                    \d+\.\d+
                )%
            )?  # capture num with . delim & ending with %
            .*
        )   # capture whole string as message
        """, re.VERBOSE)
        match = python_re.search(line)

        if match:
            match = match.groupdict()
            if (
                "progress" in match and
                match["progress"] is not None and
                match["progress"] != ""
            ):
                match['progress'] = format(
                    float(match['progress']) / 100, '.2f')
        else:
            match = {"message": line, "level": "INFO",
                     "state": None, "progress": None}
        return match

    except:

        e = sys.exc_info()[1]  # get error msg

        return {
            "message": "error '%s' on line '%s'" % (e.message, line),
            "level": "ERROR",
            "state": None,
            "progress": None
        }


def scan_output_files(workingdir, info_dict):
    """
    Scans a working directory for files as specified in the structure of the dictionary.
    using the first key as a search key, a subkey of "location" as the subdirectory,
    and another subkey of "extensions" as the file type to search. Results saved to the
    dictionary's "files" subkey.
    :param workingdir: The working directory, where output directories/files are saved
    :param dict: dictionary containing information about what files to search for. See
    delft3d-gt-server/delft3dworker/fixtures/default_template_v3.json, key "info", for
    an example of structure.
    :return: dict: now with files subkey list filled for each key
    """
    processed_files = 0
    required_keys = ["location", "extensions", "files"]
    for key, value in info_dict.items():

        # Check whether info dict is nested
        if not isinstance(value, dict):
            continue

        # and has required keys to scan for
        if not all([k in value for k in required_keys]):
            continue

        foldername = os.path.join(workingdir, value["location"])
        for root, __, files in os.walk(foldername):
            # sort to correctly order images
            for fn in sorted(files):
                name, ext = os.path.splitext(fn)

                # Check if we use this file
                if ext not in value["extensions"]:
                    continue

                # and if we already have it
                if fn in value["files"]:
                    continue

                processed_files += 1

                # If images, search by key
                # TODO Use regex expressions in the future
                if "_images" in key:
                    type_of_image = key.split("_images")[0]
                    if (type_of_image in name):
                        info_dict[key]["files"].append(fn)

                # If json, use filename as key and load json
                elif ".json" in ext:
                    with open(os.path.join(root, fn)) as f:
                        try:
                            output_dict = json.load(f)
                            info_dict[key]["files"][name] = output_dict
                        except ValueError as e:
                            logging.error("Error parsing postprocessing {}: {}".format(f, e))

                # Add files without parsing
                else:
                    info_dict[key]["files"].append(fn)

        if processed_files > 0:
            logging.info("Processed {} files.".format(processed_files))

    return info_dict


def merge_list_of_dict(a, b, key="name"):
    """A takes precedence on key collision."""
    keys = [x[key] for x in a]
    for d in b:
        if d[key] in keys:
            continue
        else:
            a.append(d)
    return a


def merge_log_unique(original, update):
    """Merge the output of log files.
    This should keep our log files quite small."""

    overlap = False

    # Split logs into lines
    o = original.split("\n")
    u = update.split("\n")

    # Find overlap
    for i, oline in enumerate(o):
        if oline == u[0]:
            overlap = True
            break

    # If overlap, merge and return
    if overlap:
        new = o[0:i]
        new.extend(u)
        return "\n".join(new)
    # Otherwise return both logs
    else:
        return original + update
