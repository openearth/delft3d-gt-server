from __future__ import absolute_import

from django.test import TestCase

from delft3dcontainermanager.tasks import delft3dgt_pulse
from delft3dcontainermanager.tasks import get_docker_ps
from delft3dcontainermanager.tasks import get_docker_log
from delft3dcontainermanager.tasks import do_docker_create
from delft3dcontainermanager.tasks import do_docker_start
from delft3dcontainermanager.tasks import do_docker_stop
from delft3dcontainermanager.tasks import do_docker_remove
from delft3dcontainermanager.tasks import do_docker_sync_filesystem


class TaskTest(TestCase):

    def test_delft3dgt_pulse(self):
        """
        TODO: write test
        """
        delay = delft3dgt_pulse.delay()
        self.assertEqual(delay.result, {})

    def test_get_docker_ps(self):
        """
        TODO: write test
        """
        delay = get_docker_ps.delay()
        self.assertEqual(delay.result, {})

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
