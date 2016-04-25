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
    match = percentage_re.search(line).groupdict()
    if float(match['progress']) > 1:
        match['progress'] = float(match['progress'])/100
    else:
        match['progress'] = float(match['progress'])
    # add default log level
    match['level'] = 'INFO'
    # add state
    match['State'] = None
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
    match = python_re.search(line).groupdict()
    if float(match['progress']) > 1:
        match['progress'] = float(match['progress'])/100
    else:
        match['progress'] = float(match['progress'])
    return match



# print delft3d_logparser('INFO:root:Time to finish 60.0, 33.3333333333% completed, time steps  left 6.0')
# print python_logparser('INFO:root:RUNNING Time to finish 60.0, 33.3333333333% completed, time steps  left 6.0')
