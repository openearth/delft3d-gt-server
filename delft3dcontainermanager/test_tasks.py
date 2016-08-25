from __future__ import absolute_import

from django.test import TestCase
from mock import patch

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
    }

    @patch('delft3dcontainermanager.tasks.Client', **mock_options)
    def test_get_docker_ps(self, mockClient):
        """
        Assert that the docker_ps task
        calls the docker client.containers() function.
        """
        get_docker_ps.delay()
        mockClient.return_value.containers.assert_called_with(all=True)

    @patch('delft3dcontainermanager.tasks.Client', **mock_options)
    def test_get_docker_log(self, mockClient):
        """
        Assert that the docker_log task
        calls the docker client.logs() function.
        """
        get_docker_log.delay("id", stdout=False, stderr=True, tail=5)
        mockClient.return_value.logs.assert_called_with(
            container="id", stdout=False, stderr=True, tail=5, stream=False,
            timestamps=True)

    def test_do_docker_create(self):
        """
        TODO: write test
        """
        delay = do_docker_create.delay("image")
        self.assertEqual(delay.result, None)

    @patch('delft3dcontainermanager.tasks.Client', **mock_options)
    def test_do_docker_start(self, mockClient):
        """
        Assert that the docker_start task
        calls the docker client.start() function
        """
        do_docker_start.delay("id")
        mockClient.return_value.start.assert_called_with(container="id")

    @patch('delft3dcontainermanager.tasks.Client', **mock_options)
    def test_do_docker_stop(self, mockClient):
        """
        Assert that the docker_stop task
        calls the docker client.stop() function
        """
        do_docker_stop.delay("id", timeout=5)
        mockClient.return_value.stop.assert_called_with(
            container="id", timeout=5)

    @patch('delft3dcontainermanager.tasks.Client', **mock_options)
    def test_do_docker_remove(self, mockClient):
        """
        Assert that the docker_remove task
        calls the docker client.remove_container() function
        """
        delay = do_docker_remove.delay("id")
        mockClient.return_value.remove_container.assert_called_with(
            container="id", force=False)
        self.assertEqual(delay.result, True)

    def test_do_docker_sync_filesystem(self):
        """
        TODO: write test
        """
        delay = do_docker_sync_filesystem.delay("id")
        self.assertEqual(delay.result, False)
