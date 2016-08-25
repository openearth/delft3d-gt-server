from __future__ import absolute_import

from django.core.management import call_command
from django.test import TestCase

from mock import patch

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
        self.container = Container.objects.create(
                    scene=self.scene,
                    docker_id='abcdefg'
                )
        self.container = Container.objects.create(
                    scene=self.scene,
                    docker_id=''
                )
        self.container = Container.objects.create(
                    scene=self.scene,
                    docker_id='hijklmn'
                )

    @patch('delft3dcontainermanager.tasks.Client', **mock_options)
    def test_containersync_sceneupdate(self, mockClient):
        """
        Test match matrix for docker containers and model containers
        """
        mockClient.return_value = [{u'Id': u'abcdefg'},{u'Id': u'opqrstu'}]
        call_command('containersync_sceneupdate')

