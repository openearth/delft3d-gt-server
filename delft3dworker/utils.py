import re

class PersistentLogger():
    """ Class to keep track of docker
    container logging, keeping relevant
    states and info.
    
    TODO stdout/stderr
    TODO filter self.info

    """

    def __init__(self, parser="delft3d"):
        if parser == "delft3d":
            self.parser = delft3d_logparser
        else:
            self.parser = python_logparser
        
        self.maxmessages = 200  # to keep
        self.severity = ["","DEBUG","INFO","WARNING","ERROR","CRITICAL"]

        # Keep track of:
        # all messages, latest and errormessage
        self.info = {
        "messages": [],
        "message": "",
        "latesterror": "",
        
        # level and highest level
        "level": "",
        "levelhigh": "",

        # progress and highest progress
        "progresshigh": 0,  # for double counters
        "progressprev": 0,
        "progress": 0,

        # state and all previous states
        "state": "START",  # if we parse, we've started
        "states": set(),
        }

    def changed(self):
        """Returns True if logging reported progress.
        It's assumed that if progress has occured, there's
        something new to process."""
        
        if self.info["progress"] > self.info["progressprev"]:
            return True
        else:
            return False

    def persistentupdate(self):
        """Updates persistent state
        based on latest parsed log."""

        # messages
        if self.info["message"] != "" or not None:
            self.info["messages"].append(self.info["message"])
        if len(self.info["messages"]) > self.maxmessages:
            self.info["messages"].pop(0)

        # levels
        l = self.severity.index(self.info["level"])
        lh = self.severity.index(self.info["levelhigh"])
        if l > lh:
            self.info["levelhigh"] = self.info["level"]

        if l >= 4:  # ERROR or CRITICAL
            self.info["latesterror"] = self.info["message"] 

        # progress
        if self.info["progress"] > self.info["progresshigh"]:
            self.info["progresshigh"] = self.info["progress"]

        # states
        self.info["states"].add(self.info['state'])

    def parse(self, logline):
        # Set fallback values
        self.info["progressprev"] = self.info["progress"]

        log = self.parser(logline)
        for key, value in log:
            if value is not None:
                self.info[key] = value

        self.persistentupdate()

        return self.info


def delft3d_logparser(line):
    """
    read progress information from delft3d log.
    :param line: parse log message
    :return: progress [0-1]
    """
    try:
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
    except:
        return {"message": None, "level": None, "state": None, "progress": None}

def python_logparser(line):
    """
    :param line: parse log message
    :return: level (string), message (string), progress [0-1] (float)(optional), state, (string)(optional)
    """
    try:
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
    except:
        return {"message": None, "level": None, "state": None, "progress": None}

