from __future__ import absolute_import

from django.core.management import call_command

from django.test import TestCase

from fakeredis import FakeStrictRedis

from mock import patch, PropertyMock

from StringIO import StringIO

from delft3dworker.models import Scenario
from delft3dworker.models import Scene
# from delft3dworker.models import Container
from delft3dworker.models import Template
from delft3dworker.models import Workflow


class ManagementTest(TestCase):
    mock_options = {
        'autospec': True,
    }

    def setUp(self):
        # self.template = Template.objects.create(
        #     name='Template'
        # )
        # self.scenario = Scenario.objects.create(
        #     name='Scenario',
        #     template=self.template
        # )
        self.scene = Scene.objects.create(
            name='Scene',
            id='0',
            # scenario=self.scenario,
            phase=Scene.phases.new
        )
        # self.container_1_1 = Container.objects.create(
        #     scene=self.scene,
        #     container_type='preprocess',
        #     docker_id='abcdefg'
        # )
        # self.container_1_0 = Container.objects.create(
        #     scene=self.scene,
        #     container_type='delft3d',
        #     docker_id=''
        # )
        # self.container_0_1 = Container.objects.create(
        #     scene=self.scene,
        #     container_type='process',
        #     docker_id='hijklmn'
        # )
        self.workflow_1_1 = Workflow.objects.create(
            scene=self.scene,
            name='abcdefg'
        )

        # self.template_new = Template.objects.create(
        #     name='Template_New'
        # )
        # self.scenario_new = Scenario.objects.create(
        #     name='Scenario_New',
        #     template=self.template_new
        # )
        # a freshly created Scene
        self.scene_new = Scene.objects.create(
            name='Scene_New',
            id='1',
            # scenario=self.scenario_new,
            phase=Scene.phases.fin
        )
        # self.container_1_1_new = Container.objects.create(
        #     scene=self.scene_new,
        #     container_type='preprocess',
        #     desired_state='created',
        #     docker_state='non-existent',
        #     docker_id=''
        # )
        # self.container_1_0_new = Container.objects.create(
        #     scene=self.scene_new,
        #     container_type='delft3d',
        #     desired_state='created',
        #     docker_state='non-existent',
        #     docker_id=''
        # )
        # self.container_0_1_new = Container.objects.create(
        #     scene=self.scene_new,
        #     container_type='process',
        #     desired_state='created',
        #     docker_state='non-existent',
        #     docker_id=''
        # )
        self.workflow_1_1_new = Workflow.objects.create(
            scene=self.scene_new,
            name='idunno',
            desired_state='running',
            cluster_state='non-existent'
        )

        self.get_redis = patch('celery_once.backends.redis.get_redis')
        self.mocked_redis = self.get_redis.start()

        self.redis = FakeStrictRedis()
        self.mocked_redis.return_value = self.redis

    # @patch('delft3dworker.management.commands.'
    #        'containersync_sceneupdate.Container.update_from_docker_snapshot')
    # @patch('delft3dcontainermanager.tasks.Client', **mock_options)
    # def test_containersync_sceneupdate(self, mockClient, mockContainerupdate):
    #     """
    #     Test match matrix for docker containers and model containers
    #     TODO: Add test case with timeout error as return_value
    #     """
    #
    #     def inspect(container=''):
    #        return {'Id': container, 'Config': {'Labels': {'type': 'preprocess'}}}
    #
    #     client = mockClient.return_value
    #     client.containers.return_value = [{'Id': 'abcdefg', 'Status': 'running',
    #                                        'Config': {'Labels': {'type': 'preprocess'}}},
    #                                       {'Id': 'orphan', 'Status': 'running',
    #                                        'Config': {'Labels': {'type': 'preprocess'}}}]
    #     client.inspect_container.side_effect = inspect
    #
    #     out = StringIO()
    #     call_command('containersync_sceneupdate', stderr=out)
    #
    #     # Docker container not in database
    #     self.assertIn(
    #         'Docker container orphan not found in database!', out.getvalue())
    #     client.remove_container.assert_called_with(
    #         container='orphan', force=True)
    #
    #     # Docker container in database
    #     self.assertEqual(mockContainerupdate.call_count, 2)
    #     mockContainerupdate.assert_called_with(
    #         {'Config': {'Labels': {'type': 'preprocess'}}, 'Id': 'abcdefg'})
    #
    # @patch('delft3dworker.management.commands.'
    #        'containersync_sceneupdate.Container.update_from_docker_snapshot')
    # @patch('delft3dcontainermanager.tasks.Client', **mock_options)
    # @patch('delft3dworker.management.commands.'
    #        'containersync_sceneupdate.AsyncResult')
    # def test_containersync_scenekill(self, mockAsync, mockClient, mockContainerupdate):
    #     """
    #     Test match matrix for docker containers and model containers
    #     TODO: Add test case with timeout error as return_value
    #     """
    #
    #     client = mockClient.return_value
    #     client.containers.return_value = [{'Id': 'abcdefg', 'Status': 'running',
    #                                        'Config': {'Labels': {'type': 'notfromhere'}}},
    #                                       {'Id': 'orphan', 'Status': 'running',
    #                                        'Config': {'Labels': {'type': 'notfromhere'}}}]
    #
    #     def getresult():
    #         return {'status': 'SUCCESS'}
    #
    #     # Mock celery result
    #     result = mockAsync.return_value
    #     result._get_task_meta.side_effect = getresult
    #     result.result = client.containers.return_value
    #
    #     out = StringIO()
    #     call_command('containersync_sceneupdate', stderr=out)
    #
    #     # Docker container not in database
    #     assert not client.remove_container.called
    #
    # @patch('delft3dworker.management.commands.'
    #        'containersync_sceneupdate.Scene._local_scan_process')
    # def test_scanbucket_command(self, mocklocalscan):
    #     call_command('scanbucket')
    #
    #     self.assertEqual(mocklocalscan.call_count, 1)


    @patch('delft3dworker.management.commands.'
           'sync_cluster_state.Workflow.sync_cluster_state')
    @patch('delft3dcontainermanager.tasks.client.CoreV1Api', **mock_options)
    def test_sync_cluster_state(self, mockClient, mockWorkflowupdate):
        """
        Test match matrix for argo workflow and model workflow
        """
        # def inspect(workflow=''):
        #    return {'metadata':{'name': workflow}}

        client = mockClient.return_value
        print(client)
        client.api_client.call_api.return_value = [{'metadata':{'name':'abcdefg', 'labels': {u'workflows.argoproj.io/phase': 'Running'}}},
                               {'metadata':{'name':'orphan', 'labels': {u'workflows.argoproj.io/phase': 'Running'}}}]
        print(client)
        # client.side_effect = inspect

        out = StringIO()
        call_command('sync_cluster_state', stderr=out)

        # Workflow not in database
        self.assertIn(
            'Workflow orphan not found in database!', out.getvalue())
        client.remove_workflow.assert_called_with(
            container='orphan', force=True)

        # workflow in database
        self.assertEqual(mockWorkflowupdate.call_count, 2)
        mockWorkflowupdate.assert_called_with(
            {'metadata': {'name': 'abcdefg', 'labels': {u'workflows.argoproj.io/phase': 'Running'}}}
        )


    def tearDown(self):
        self.redis.flushall()
        self.get_redis.stop()
