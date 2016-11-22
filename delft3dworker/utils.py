import re
import sys
from django.conf import settings


def version_default():
    # default value for JSONField of Container model
    return {'REPOS_URL': settings.REPOS_URL,
            'SVN_REV': settings.SVN_REV}


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
