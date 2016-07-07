import os

from django.conf import settings
from django.test import TestCase

from mock import patch

from celery import current_app
from delft3dworker.tasks import chainedtask, dummy

# Main thing to test here is the valid forking in
# the tasks and its return values.

# Hard thing to do is to mock Docker

class TaskTest(TestCase):

    def setUp(self):
        # Run celery tasks directly
        settings.CELERY_ALWAYS_EAGER = True
        current_app.conf.CELERY_ALWAYS_EAGER = True

        # Are normally from provisioning
        settings.DELFT3D_DUMMY_IMAGE_NAME = 'dummy_simulation'
        settings.POSTPROCESS_DUMMY_IMAGE_NAME = 'dummy_postprocessing'
        settings.PREPROCESS_DUMMY_IMAGE_NAME = 'dummy_preprocessing'
        settings.PROCESS_DUMMY_IMAGE_NAME = 'dummy_processing'
        settings.EXPORT_DUMMY_IMAGE_NAME = 'dummy_export'

    def test_dummy(self):
        delay = dummy.delay()
        self.assertTrue(delay.result is None)

    def getFalse(self):
        return False

    @patch('delft3dworker.tasks.DockerClient', autospec=True)
    def test_chainedtask(self, mockDockerClient):
        # Autospec cant do init
        mockDockerClient.return_value.id = '1238761287361'
        mockDockerClient.return_value.running = self.getFalse

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
