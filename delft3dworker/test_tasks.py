from __future__ import absolute_import

import os
from celery import current_app
from django.conf import settings
from django.test import TestCase

from mock import patch

from delft3dworker.tasks import chainedtask, dummy, DockerClient


# Main thing to test here is the valid forking in
# the tasks and its return values.

# Hard thing to do is to mock Docker

class DockerTest(TestCase):

    @patch('delft3dworker.tasks.Client', autospec=True, create=True)
    def setUp(self, mockClient):
        mockClient.return_value.inspect_container.return_value = {
            "State": {"Running": True}}
        mockClient.return_value.create_container.return_value = {
            "Id": 22, "State": {"Running": True}}
        self.client = DockerClient('docker', {}, 'output', 'command', tail=2)

    def testdocker(self):
        self.client.start()
        self.assertTrue(self.client.running())
        self.assertTrue(isinstance(self.client.status(), dict))
        self.client.stop()
        self.client.delete()


class TaskTest(TestCase):

    # Broken: Models don't create directories anymore, so this test fails
    # TODO: Fix these tests
    # def test_dummy(self):
    #     delay = dummy.delay()
    #     self.assertTrue(delay.result is None)

    def getFalse(self):
        return False

    # Broken: Models don't create directories anymore, so this test fails
    # TODO: Fix these tests
    # @patch('delft3dworker.tasks.chainedtask.app.control.inspect',
    #        autospec=False, create=True)
    # @patch('delft3dworker.tasks.DockerClient', autospec=True)
    # def test_chainedtask(self, mockDockerClient, mockControl):
    #     # Autospec cant do init
    #     mockDockerClient.return_value.id = '1238761287361'
    #     mockDockerClient.return_value.running = self.getFalse

    #     # No workflow given
    #     parameters = ["a", {}, os.getcwd(), '']
    #     delay = chainedtask.delay(*parameters)
    #     self.assertTrue(delay.result is None)

    #     # Export workflow
    #     parameters = ["a", {}, os.getcwd(), 'export']
    #     delay = chainedtask.delay(*parameters)
    #     self.assertTrue("result" in delay.result)
    #     self.assertTrue(delay.result['result'] == "Finished")

    #     # Main workflow
    #     parameters = ["a", {}, os.getcwd(), 'main']
    #     delay = chainedtask.delay(*parameters)
    #     self.assertTrue("result" in delay.result)
    #     self.assertTrue(delay.result['result'] == "Finished")

    #     # Dummy workflow
    #     parameters = ["a", {}, os.getcwd(), 'dummy']
    #     delay = chainedtask.delay(*parameters)
    #     self.assertTrue("result" in delay.result)
    #     self.assertTrue(delay.result['result'] == "Finished")

    #     # Dummy export workflow
    #     parameters = ["a", {}, os.getcwd(), 'dummy_export']
    #     delay = chainedtask.delay(*parameters)
    #     self.assertTrue("result" in delay.result)
    #     self.assertTrue(delay.result['result'] == "Finished")
