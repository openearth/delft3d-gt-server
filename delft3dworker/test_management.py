from __future__ import absolute_import

from django.core.management import call_command

from django.test import TestCase

from fakeredis import FakeStrictRedis

from mock import patch

from StringIO import StringIO

from delft3dworker.models import Scene
from delft3dworker.models import Container


class ManagementTest(TestCase):
    mock_options = {
        'autospec': True,
    }

    def setUp(self):
        self.scene = Scene.objects.create(
            name='Scene',
            phase=Scene.phases.new
        )
        self.container_1_1 = Container.objects.create(
            scene=self.scene,
            container_type='preprocess',
            docker_id='abcdefg'
        )
        self.container_1_0 = Container.objects.create(
            scene=self.scene,
            container_type='delft3d',
            docker_id=''
        )
        self.container_0_1 = Container.objects.create(
            scene=self.scene,
            container_type='process',
            docker_id='hijklmn'
        )

        # a freshly created Scene
        self.scene_new = Scene.objects.create(
            name='Scene_New',
            phase=Scene.phases.fin
        )
        self.container_1_1_new = Container.objects.create(
            scene=self.scene_new,
            container_type='preprocess',
            desired_state='created',
            docker_state='non-existent',
            docker_id=''
        )
        self.container_1_0_new = Container.objects.create(
            scene=self.scene_new,
            container_type='delft3d',
            desired_state='created',
            docker_state='non-existent',
            docker_id=''
        )
        self.container_0_1_new = Container.objects.create(
            scene=self.scene_new,
            container_type='process',
            desired_state='created',
            docker_state='non-existent',
            docker_id=''
        )

    @patch('delft3dworker.management.commands.'
           'containersync_sceneupdate.Container.update_from_docker_snapshot')
    @patch('delft3dcontainermanager.tasks.Client', **mock_options)
    @patch('delft3dworker.management.commands.'
           'containersync_sceneupdate.AsyncResult')
    @patch('delft3dcontainermanager.tasks.QueueOnce.redis', new_callable=FakeStrictRedis)
    def test_containersync_sceneupdate(self, mockRedis, mockAsync, mockClient, mockContainerupdate):
        """
        Test match matrix for docker containers and model containers
        TODO: Add test case with timeout error as return_value
        """
        client = mockClient.return_value
        client.containers.return_value = [{'Id': 'abcdefg', 'Status': 'running',
                                           'Config': {'Labels': {'type': 'preprocess'}}},
                                          {'Id': 'orphan', 'Status': 'running',
                                           'Config': {'Labels': {'type': 'preprocess'}}}]

        def getresult():
            return {'status': 'SUCCESS'}

        # Mock celery result
        result = mockAsync.return_value
        result._get_task_meta.side_effect = getresult
        result.result = client.containers.return_value

        out = StringIO()
        call_command('containersync_sceneupdate', stderr=out)

        # Docker container not in database
        self.assertIn(
            'Docker container orphan not found in database!', out.getvalue())
        client.remove_container.assert_called_with(
            container='orphan', force=True)

        # Docker container in database
        self.assertEqual(mockContainerupdate.call_count, 6)
        mockContainerupdate.assert_called_with(
            {'Id': 'abcdefg', 'Status': 'running', 'Config': {'Labels': {'type': 'preprocess'}}})

    @patch('delft3dworker.management.commands.'
           'containersync_sceneupdate.Container.update_from_docker_snapshot')
    @patch('delft3dcontainermanager.tasks.Client', **mock_options)
    @patch('delft3dworker.management.commands.'
           'containersync_sceneupdate.AsyncResult')
    @patch('delft3dcontainermanager.tasks.QueueOnce.redis', new_callable=FakeStrictRedis)
    def test_containersync_scenekill(self, mockRedis, mockAsync, mockClient, mockContainerupdate):
        """
        Test match matrix for docker containers and model containers
        TODO: Add test case with timeout error as return_value
        """
        client = mockClient.return_value
        client.containers.return_value = [{'Id': 'abcdefg', 'Status': 'running',
                                           'Config': {'Labels': {'type': 'notfromhere'}}},
                                          {'Id': 'orphan', 'Status': 'running',
                                           'Config': {'Labels': {'type': 'notfromhere'}}}]

        def getresult():
            return {'status': 'SUCCESS'}

        # Mock celery result
        result = mockAsync.return_value
        result._get_task_meta.side_effect = getresult
        result.result = client.containers.return_value

        out = StringIO()
        call_command('containersync_sceneupdate', stderr=out)

        # Docker container not in database
        assert not client.remove_container.called

    @patch('delft3dworker.management.commands.'
           'containersync_sceneupdate.Scene._local_scan_process')
    def test_scanbucket_command(self, mocklocalscan):
        call_command('scanbucket')

        self.assertEqual(mocklocalscan.call_count, 1)
