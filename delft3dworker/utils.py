import re

def progress_from_delft3d_log(line):
    """
    read progress information from delft3d log.
    :param line: parse log message
    :return: progress [0-1]
    """
    percentage_re = re.compile(r'(?P<progress>[\d\.]+)\%')
    match = percentage_re.search(line)
    if match is None:
        return None
    progress = match.groupdict()['progress']
    progress = float(progress)
    return progress