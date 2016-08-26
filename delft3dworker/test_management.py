from __future__ import absolute_import

from django.core.management import call_command

from django.test import TestCase

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
        )
        self.container_1_1 = Container.objects.create(
            scene=self.scene,
            docker_id='abcdefg'
        )
        self.container_1_0 = Container.objects.create(
            scene=self.scene,
            docker_id=''
        )
        self.container_0_1 = Container.objects.create(
            scene=self.scene,
            docker_id='hijklmn'
        )

    @patch('delft3dworker.management.commands.'
        'containersync_sceneupdate.Container._update_state_and_save')
    @patch('delft3dcontainermanager.tasks.Client', **mock_options)
    def test_containersync_sceneupdate(self, mockClient, mockContainerupdate):
        """
        Test match matrix for docker containers and model containers
        """
        client = mockClient.return_value
        client.containers.return_value = [{'Id': 'abcdefg'},
                                          {'Id': 'orphan'}]

        out = StringIO()
        call_command('containersync_sceneupdate', stderr=out)

        # Docker container not in database
        self.assertIn(
            'Docker container orphan not found in database!', out.getvalue())
        client.remove_container.assert_called_with(
            container='orphan', force=True)

        # Docker container in database
        mockContainerupdate.assert_called_with({'Id': 'abcdefg'})
