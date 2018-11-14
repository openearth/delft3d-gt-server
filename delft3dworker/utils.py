import os
import re
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
    # default value for JSONField of Container model
    return {'REPOS_URL': settings.REPOS_URL,
            'SVN_REV': settings.SVN_REV,
            'PRE_REV': settings.SVN_PRE_REV,
            'PROC_REV': settings.SVN_PROC_REV,
            'POST_REV': settings.SVN_POST_REV,
            'EXP_REV': settings.SVN_EXP_REV,
            'delft3d_version': settings.DELFT3D_VERSION}


def get_version(container_type):
    container_types = {
        'delft3d': {
            "delft3d_version": settings.DELFT3D_VERSION},

        'export': {
            'REPOS_URL': settings.REPOS_URL,
            'SVN_REV': settings.SVN_EXP_REV, },

        'postprocess': {
            'REPOS_URL': settings.REPOS_URL,
            'SVN_REV': settings.SVN_POST_REV, },

        'preprocess': {
            'REPOS_URL': settings.REPOS_URL,
            'SVN_REV': settings.SVN_PRE_REV, },

        'sync_cleanup': {},

        'process': {
            'REPOS_URL': settings.REPOS_URL,
            'SVN_REV': settings.SVN_PROC_REV, },
    }
    return container_types[container_type] if container_type in container_types else {}

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

def scan_output_files(workingdir, dict):
    """
    Scans a working directory for files as specified in the structure of the dictionary.
    using the first key as a search key, a subkey of "location" as the subdirectory,
    and another subkey of "extensions" as the file type to search. Results saved to the
    dictionary's "files" subkey.
    :param workingdir: The working directory, where output directories/files are saved
    :param dict: dictionary containing information about what files to search for. See
    delft3d-gt-server/delft3dworker/fixtures/default_template_v3.json, key "info", for
    an example of structure.
    :return:
    """
    for key in dict:
        if "_images" in key:
            search_key = key.split("_images")[0]
        elif "log" in key:
            search_key = dict[key]["filename"]
        else:
            search_key = key

        for root, dirs, files in os.walk(
                os.path.join(workingdir, dict[key]["location"])
        ):
            for f in sorted(files):
                name, ext = os.path.splitext(f)
                if ext in (dict[key]["extensions"]):
                    if (search_key in name and f not in dict[key]["files"]):
                        dict[key]["files"].append(f)

    return dict