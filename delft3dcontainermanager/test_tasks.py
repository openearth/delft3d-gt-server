from __future__ import absolute_import

import os

from django.test import TestCase
from fakeredis import FakeStrictRedis
from mock import patch
from six.moves import configparser

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
    }

    @patch('delft3dcontainermanager.tasks.call_command')
    @patch('delft3dcontainermanager.tasks.QueueOnce.redis')
    def test_delft3dgt_pulse(self, mockredis, mockcall):
        """
        Assert that de delft3dgt_pulse task
        calls the containersync_sceneupdate() function.
        """
        fake = FakeStrictRedis()
        mockredis.return_value = fake

        delft3dgt_pulse.delay()
        mockcall.assert_called_with('containersync_sceneupdate')

    @patch('delft3dcontainermanager.tasks.Client', **mock_options)
    @patch('delft3dcontainermanager.tasks.logging.error', **mock_options)
    def test_get_docker_ps(self, mockLogging, mockClient):
        """
        Assert that the docker_ps task
        calls the docker client.containers() function.
        """
        containers = [{'Id':'Aaa', 'Status':'Running'},
                      {'Id':'Bbb', 'Status':'Host Down'},
                      {'Id':'Ccc', 'Status':'Up'},
                     ]

        def inspect(container=''):
            if container == 'Ccc':
                raise
            else:
                return {'Id': container, 'Config': {'Labels': {'type': 'preprocess'}}}

        mockClient.return_value.containers.return_value = containers
        mockClient.return_value.inspect_container.side_effect = inspect

        get_docker_ps.delay()
        # Call docker ps for all containers, but only once
        mockClient.return_value.containers.assert_called_with(all=True)
        self.assertEqual(mockClient.return_value.containers.call_count, 1)
        # Call inspect for all but Host Down container
        self.assertEqual(mockClient.return_value.inspect_container.call_count, 2)
        # Log error only for Ccc container
        self.assertEqual(mockLogging.call_count, 1)
    
    @patch('delft3dcontainermanager.tasks.Client', **mock_options)
    def test_get_docker_log(self, mockClient):
        """
        Assert that the docker_log task
        calls the docker client.logs() function.
        """
        get_docker_log.delay("id", stdout=False, stderr=True)
        mockClient.return_value.logs.assert_called_with(
            container="id", stdout=False, stderr=True, stream=False,
            timestamps=True, tail=5)

    @patch('delft3dcontainermanager.tasks.Client', **mock_options)
    def test_do_docker_create(self, mockClient):
        """
        Assert that the docker_create task
        calls the docker client.create_container() function.
        """
        image = "IMAGENAME"
        volumes = ['/:/data/output:z',
                   '/:/data/input:ro']
        memory_limit = '1g'
        command = "echo test"
        config = {}
        environment = None
        label = {"type": "delft3d"}
        folder = ['input', 'output']
        name = 'test-8172318273'
        workingdir = os.path.join(os.getcwd(), 'test')
        folders = [os.path.join(workingdir, f) for f in folder]
        parameters = {u'test':
                      {u'1': u'a', u'2': u'b', 'units': 'ignoreme'}
                      }
        mockClient.return_value.create_host_config.return_value = config

        do_docker_create.delay(label, parameters, None, name,
                               image, volumes, memory_limit, folders, command)

        # Assert that docker is called
        mockClient.return_value.create_container.assert_called_with(
            image,
            host_config=config,
            command=command,
            name=name,
            environment=environment,
            labels=label
        )

        # Assert that folders are created
        listdir = os.listdir(workingdir)
        for f in listdir:
            self.assertIn(f, listdir)

        for folder in folders:
            ini = os.path.join(folder, 'input.ini')
            self.assertTrue(os.path.isfile(ini))

            config = configparser.SafeConfigParser()
            config.readfp(open(ini))
            for key in parameters.keys():
                self.assertTrue(config.has_section(key))
                for option, value in parameters[key].items():
                    if option != 'units':
                        self.assertTrue(config.has_option(key, option))
                        self.assertEqual(config.get(key, option), value)
                    else:  # units should be ignored
                        self.assertFalse(config.has_option(key, option))

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
        container, log = delay.result
        self.assertEqual(container, "id")
        self.assertEqual(log, "")

    def test_do_docker_sync_filesystem(self):
        """
        TODO: write test
        """
        delay = do_docker_sync_filesystem.delay("id")
        container, log = delay.result
        self.assertEqual(container, "id")
        self.assertEqual(log, "")
