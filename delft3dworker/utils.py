import re


def delft3d_logparser(line):
    """
    read progress information from delft3d log.
    :param line: parse log message
    :return: progress [0-1]
    """
    percentage_re = re.compile(r"""
    ^(?P<message>.*?        # capture whole string as message
    (?P<progress>[\d\.]+)%  # capture number with . delimiter and ending with % as percentage
    .*
    )
    """, re.VERBOSE)
    match = percentage_re.search(line)
    if match:
        match = match.groupdict()
        if float(match['progress']) > 1:
            match['progress'] = format(float(match['progress'])/100, '.2f')
        else:
            match['progress'] = float(match['progress'])
        # add default log level
        match['level'] = 'INFO'
        # add state
        match['State'] = None
    else:
        match = {"message": None, "level": None, "state": None, "progress": None}
    return match


def python_logparser(line):
    """
    :param line: parse log message
    :return: level (string), message (string), progress [0-1] (float)(optional), state, (string)(optional)
    """
    python_re = re.compile(r"""
    ^(?P<message>               # capture whole string as message
    (?P<level>[A-Z]+)           # capture first capital word as log level
    :\w*:                       #
    (?P<state>[A-Z]*\b)?        # capture second capital word as log state
    .*?                         #
    (?P<progress>\d+\.\d+)?%    # capture number with . delimiter and ending with % as percentage
    .*)                         #
    """, re.VERBOSE)
    match = python_re.search(line)
    if match:
        match = match.groupdict()
        if float(match['progress']) > 1:
            match['progress'] = format(float(match['progress'])/100, '.2f')
        else:
            match['progress'] = float(match['progress'])
    else:
        match = {"message": None, "level": None, "state": None, "progress": None}
    return match
