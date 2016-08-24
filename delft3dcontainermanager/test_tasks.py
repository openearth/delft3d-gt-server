from __future__ import absolute_import

from django.test import TestCase
from mock import patch

from delft3dcontainermanager.tasks import delft3dgt_pulse
from delft3dcontainermanager.tasks import get_docker_ps
from delft3dcontainermanager.tasks import get_docker_log
from delft3dcontainermanager.tasks import do_docker_create
from delft3dcontainermanager.tasks import do_docker_start
from delft3dcontainermanager.tasks import do_docker_stop
from delft3dcontainermanager.tasks import do_docker_remove
from delft3dcontainermanager.tasks import do_docker_sync_filesystem


class TaskTest(TestCase):
    mock_options = {
        'autospec': True,
        # 'containers.return_value': [{'a': 'test'}]
    }

    def test_delft3dgt_pulse(self):
        """
        TODO: write test
        """
        delay = delft3dgt_pulse.delay()
        self.assertEqual(delay.result, {})


    @patch('delft3dcontainermanager.tasks.Client', **mock_options)
    def test_get_docker_ps(self, mockClient):
        """
        Assert that the docker_ps task
        calls the docker client.containers() function.
        """
        get_docker_ps.delay()
        mockClient.return_value.containers.assert_called_with(all=True)

    def test_get_docker_log(self):
        """
        TODO: write test
        """
        delay = get_docker_log.delay("id")
        self.assertEqual(delay.result, {})

    def test_do_docker_create(self):
        """
        TODO: write test
        """
        delay = do_docker_create.delay("image")
        self.assertEqual(delay.result, None)

    def test_do_docker_start(self):
        """
        TODO: write test
        """
        delay = do_docker_start.delay("id")
        self.assertEqual(delay.result, False)

    def test_do_docker_stop(self):
        """
        TODO: write test
        """
        delay = do_docker_stop.delay("id")
        self.assertEqual(delay.result, False)

    def test_do_docker_remove(self):
        """
        TODO: write test
        """
        delay = do_docker_remove.delay("id")
        self.assertEqual(delay.result, False)

    def test_do_docker_sync_filesystem(self):
        """
        TODO: write test
        """
        delay = do_docker_sync_filesystem.delay("id")
        self.assertEqual(delay.result, False)
