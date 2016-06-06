from django.conf import settings
from django.test import TestCase

from mock import patch, MagicMock, create_autospec

from celery import current_app
from delft3dworker.tasks import chainedtask, dummy
from delft3dworker.tasks import DockerClient

# Main thing to test here is the valid forking in
# the tasks and its return values.

# Hard thing to do is to mock Docker

class TaskTest(TestCase):

    def setUp(self):
        # mockDockerClient = create_autospec(DockerClient)
        settings.CELERY_ALWAYS_EAGER = True
        current_app.conf.CELERY_ALWAYS_EAGER = True

    def test_dummy(self):
        delay = dummy.delay()
        self.assertTrue(delay.result is None)

    @patch('delft3dworker.tasks.DockerClient', autospec=True)
    def test_chainedtask(self, mockDockerClient):
        parameters = ['.', {}, 'main']
        delay = chainedtask.delay(self.parameters, self.workingdir, workflow)
