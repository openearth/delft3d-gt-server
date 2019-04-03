from __future__ import absolute_import

from django.core.management import call_command

from django.test import TestCase

from fakeredis import FakeStrictRedis

from mock import patch, PropertyMock, call

# from StringIO import StringIO
from io import StringIO

from delft3dworker.models import Scenario
from delft3dworker.models import Scene
from delft3dworker.models import Template
from delft3dworker.models import Workflow


class ManagementTest(TestCase):
    mock_options = {
        'autospec': True,
    }

    def setUp(self):
        self.template = Template.objects.create(
            name='Template'
        )
        self.scenario = Scenario.objects.create(
            name='Scenario',
            template=self.template
        )

        self.scene = Scene.objects.create(
            name='Scene',
            id='0',
            phase=Scene.phases.new
        )
        self.scene.scenario.set([self.scenario])
        self.workflow_1_1 = Workflow.objects.create(
            scene=self.scene,
            name='abcdefg'
        )

        self.scene_new = Scene.objects.create(
            name='Scene_New',
            id='1',
            phase=Scene.phases.fin
        )
        self.scene_new.scenario.set([self.scenario])
        self.workflow_1_1_new = Workflow.objects.create(
            scene=self.scene_new,
            name='bar',
        )

        self.get_redis = patch('celery_once.backends.redis.get_redis')
        self.mocked_redis = self.get_redis.start()

        self.redis = FakeStrictRedis()
        self.mocked_redis.return_value = self.redis

    @patch('delft3dworker.management.commands.'
           'sync_cluster_state.Scene._local_scan_files')
    def test_scanbucket_command(self, mocklocalscan):
        call_command('scanbucket')
        self.assertEqual(mocklocalscan.call_count, 1)


    @patch('delft3dworker.management.commands.'
           'sync_cluster_state.Workflow.sync_cluster_state')
    @patch('delft3dworker.management.commands.'
           'sync_cluster_state.get_argo_workflows', **mock_options)
    @patch('delft3dworker.management.commands.'
           'sync_cluster_state.do_argo_remove', **mock_options)
    def test_sync_cluster_state(self, mockWorkflowremove, mockWorkflows, mockWorkflowupdate):
        """
        Test match matrix for argo workflow and model workflow
        """

        # Mock return of all workflows
        mockWorkflows.apply_async().result = {"get_argo_workflows": """{"items":[{"metadata":{"name":"abcdefg", "labels": {"workflows.argoproj.io/phase": "Running"}}},
                               {"metadata":{"name":"orphan", "labels": {"workflows.argoproj.io/phase": "Running"}}}]}"""}

        out = StringIO()
        call_command('sync_cluster_state', stderr=out)

        # Workflow not in database
        self.assertIn(
            'Workflow orphan not found in database!', out.getvalue())

        # workflow in database
        self.assertEqual(mockWorkflowupdate.call_count, 2)
        mockWorkflowupdate.assert_has_calls(
            [
                call({'metadata': {'name': 'abcdefg', 'labels': {u'workflows.argoproj.io/phase': 'Running'}}}),
                call(None)
            ],
            any_order=True
        )
        self.assertEqual(mockWorkflowremove.call_count, 1)


    def tearDown(self):
        self.redis.flushall()
        self.get_redis.stop()
