from __future__ import absolute_import

import os

from django.conf import settings
from django.test import TestCase

from mock import patch

from delft3dworker.tasks import chainedtask, dummy


# Main thing to test here is the valid forking in
# the tasks and its return values.

# Hard thing to do is to mock Docker

class TaskTest(TestCase):

    def test_dummy(self):
        delay = dummy.delay()
        self.assertTrue(delay.result is None)

    def getFalse(self):
        return False

    @patch('celery.app.control.Control', autospec=False)
    @patch('delft3dworker.tasks.DockerClient', autospec=True)
    def test_chainedtask(self, mockDockerClient, mockControl):
        # Autospec cant do init
        mockDockerClient.return_value.id = '1238761287361'
        mockDockerClient.return_value.running = self.getFalse

        # If we want to test revoke and aborts
        # mockControl.return_value.inspect.revoked = []

        # No workflow given
        parameters = [{}, os.getcwd(), '']
        delay = chainedtask.delay(*parameters)
        self.assertTrue(delay.result is None)

        # Export workflow
        parameters = [{}, os.getcwd(), 'export']
        delay = chainedtask.delay(*parameters)
        self.assertTrue("result" in delay.result)
        self.assertTrue(delay.result['result'] == "Finished")

        # Main workflow
        parameters = [{}, os.getcwd(), 'main']
        delay = chainedtask.delay(*parameters)
        self.assertTrue("result" in delay.result)
        self.assertTrue(delay.result['result'] == "Finished")

        # Dummy workflow
        parameters = [{}, os.getcwd(), 'dummy']
        delay = chainedtask.delay(*parameters)
        self.assertTrue("result" in delay.result)
        self.assertTrue(delay.result['result'] == "Finished")

        # Dummy export workflow
        parameters = [{}, os.getcwd(), 'dummy_export']
        delay = chainedtask.delay(*parameters)
        self.assertTrue("result" in delay.result)
        self.assertTrue(delay.result['result'] == "Finished")
