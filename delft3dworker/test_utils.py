from delft3dworker.utils import delft3d_logparser
from delft3dworker.utils import PersistentLogger

from django.test import TestCase


class LogTests(TestCase):

    def testLogParse(self):
        """
        Test if progress can be read from logfile
        """
        log = """
INFO:root:Write netcdf
INFO:root:Time to finish 90.0, 0.0% completed, time steps  left 9.0
INFO:root:Time to finish 80.0, 11.1111111111% completed, time steps  left 8.0
INFO:root:Time to finish 70.0, 22.2222222222% completed, time steps  left 7.0
INFO:root:Time to finish 60.0, 33.3333333333% completed, time steps  left 6.0
INFO:root:Time to finish 50.0, 44.4444444444% completed, time steps  left 5.0
INFO:root:Time to finish 40.0, 55.5555555556% completed, time steps  left 4.0
INFO:root:Time to finish 30.0, 66.6666666667% completed, time steps  left 3.0
INFO:root:Time to finish 20.0, 77.7777777778% completed, time steps  left 2.0
INFO:root:Time to finish 10.0, 88.8888888889% completed, time steps  left 1.0
INFO:root:Time to finish 0.0, 100.0% completed, time steps  left 0.0
INFO:root:Finished
        """

        progresses = []
        messages = []
        for line in log.splitlines():
            match = delft3d_logparser(line)
            if match['progress'] is not None:
                progresses.append(match['progress'])
            messages.append(match['message'])
        self.assertTrue(
            any(True for progress in progresses if float(progress) < 0.001))
        self.assertTrue(
            any(True for progress in progresses if float(progress) > 0.99))
        self.assertTrue(
            any(True for message in messages if message is not None))
