from __future__ import absolute_import

import json
import os
import uuid
import yaml
import zipfile
from datetime import timedelta

from django.conf import settings
from constance import config as cconfig
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import TestCase
from django.utils.timezone import now

from guardian.shortcuts import assign_perm
from guardian.shortcuts import get_objects_for_user

from mock import Mock
from mock import patch

from delft3dworker.models import Scenario
from delft3dworker.models import Scene
from delft3dworker.models import Workflow
from delft3dworker.models import SearchForm
from delft3dworker.models import Template
from delft3dworker.models import User


class ScenarioTestCase(TestCase):

    def setUp(self):
        self.user_foo = User.objects.create_user(username='foo')
        self.template = Template.objects.create(name="Template parent")
        self.scenario_single = Scenario.objects.create(
            name="Test single scene", owner=self.user_foo, template=self.template)
        self.scenario_multi = Scenario.objects.create(
            name="Test multiple scenes", owner=self.user_foo, template=self.template)
        self.scenario_A = Scenario.objects.create(
            name="Test hash A", owner=self.user_foo, template=self.template)
        self.scenario_B = Scenario.objects.create(
            name="Test hash B", owner=self.user_foo, template=self.template)

    def test_scenario_parses_input(self):
        """Correctly parse scenario input"""

        # This should create only one scene
        single_input = {
            "basinslope": {
                "values": 0.0143
            },
        }

        # This should create 3 scenes
        multi_input = {
            "basinslope": {
                "values": [0.0143, 0.0145, 0.0146]
            },
        }

        self.scenario_single.load_settings(single_input)
        self.scenario_multi.load_settings(multi_input)

        self.assertEqual(len(self.scenario_single.scenes_parameters), 1)
        self.assertEqual(len(self.scenario_multi.scenes_parameters), 3)

    def test_hash_scenes(self):
        """Test if scene clone is detected and thus has both Scenarios."""

        single_input = {
            "basinslope": {
                "group": "",
                "maxstep": 0.3,
                "minstep": 0.01,
                "stepinterval": 0.1,
                "units": "deg",
                "useautostep": False,
                "valid": True,
                "value": 0.0143
            },
        }

        self.scenario_A.load_settings(single_input)
        self.scenario_A.createscenes(self.user_foo)

        self.scenario_B.load_settings(single_input)
        self.scenario_B.createscenes(self.user_foo)

        scene = self.scenario_B.scene_set.all()[0]
        self.assertIn(self.scenario_A, scene.scenario.all())
        self.assertIn(self.scenario_B, scene.scenario.all())


class ScenarioControlTestCase(TestCase):

    def setUp(self):
        self.user_foo = User.objects.create_user(username='foo')

        self.template = Template.objects.create(name="bar")
        self.scenario_multi = Scenario.objects.create(
            name="Test multiple scenes", owner=self.user_foo, template=self.template)
        multi_input = {
            "basinslope": {
                "values": [0.0143, 0.0145, 0.0146]
            },
        }
        self.scenario_multi.load_settings(multi_input)
        self.scenario_multi.createscenes(self.user_foo)

    @patch('delft3dworker.models.Scene.start', autospec=True)
    def test_start(self, mocked_scene_method):
        """
        Test if scenes are started when scenario is started
        """
        self.scenario_multi.start(self.user_foo)
        self.assertEqual(mocked_scene_method.call_count, 3)

    @patch('delft3dworker.models.Scene.redo_proc', autospec=True)
    def redo_proc(self, mocked_scene_method):
        """
        Test if redo_proc is called when processing for scenario is started
        """
        self.scenario_multi.redo_proc(self.user_foo)
        self.asserEqual(mocked_scene_method.call_count, 3)

    @patch('delft3dworker.models.Scene.redo_postproc', autospec=True)
    def redo_postproc(self, mocked_scene_method):
        """
        Test if redo_postproc is called when postprocessing for scenario is started
        """
        self.scenario_multi.redo_postproc(self.user_foo)
        self.asserEqual(mocked_scene_method.call_count, 3)

    @patch('delft3dworker.models.Scene.abort', autospec=True)
    def test_abort(self, mocked_scene_method):
        """
        Test if scenes are aborted when scenario is aborted
        """
        self.scenario_multi.abort(self.user_foo)
        self.assertEqual(mocked_scene_method.call_count, 3)

    @patch('delft3dworker.models.Scene.delete', autospec=True)
    def test_delete(self, mocked_scene_method):
        """
        Test if scenes are deleted when scenario is deleted
        """
        self.scenario_multi.delete(self.user_foo)
        self.assertEqual(mocked_scene_method.call_count, 3)

    @patch('delft3dworker.models.Scene.publish_company', autospec=True)
    def test_publish_company(self, mocked_scene_method):
        """
        Test if scenes are published to company when scenario is published
        to company
        """
        self.scenario_multi.publish_company(self.user_foo)
        self.assertEqual(mocked_scene_method.call_count, 3)

    @patch('delft3dworker.models.Scene.publish_world', autospec=True)
    def test_publish_world(self, mocked_scene_method):
        """
        Test if scenes are published to world when scenario is published
        to world
        """
        self.scenario_multi.publish_world(self.user_foo)
        self.assertEqual(mocked_scene_method.call_count, 3)


class SceneTestCase(TestCase):

    def setUp(self):

        # create users, groups and assign permissions
        self.user_a = User.objects.create_user(username='A')
        self.user_b = User.objects.create_user(username='B')
        self.user_c = User.objects.create_user(username='C')

        company_w = Group.objects.create(name='access:world')
        for user in [self.user_a, self.user_b, self.user_c]:
            company_w.user_set.add(user)
            for perm in ['view_scene', 'add_scene',
                         'change_scene', 'delete_scene']:
                user.user_permissions.add(
                    Permission.objects.get(codename=perm)
                )

        company_x = Group.objects.create(name='access:org:Company X')
        company_x.user_set.add(self.user_a)
        company_x.user_set.add(self.user_b)
        company_y = Group.objects.create(name='access:org:Company Y')
        company_y.user_set.add(self.user_c)

        # scene
        self.scene_1 = Scene.objects.create(
            name='Scene 1',
            owner=self.user_a,
            shared='p',
            phase=Scene.phases.fin,
            entrypoint=Scene.entrypoints.main
        )
        self.scene_2 = Scene.objects.create(
            name='Scene 2',
            owner=self.user_a,
            shared='p',
            phase=Scene.phases.idle,
            entrypoint=Scene.entrypoints.main
        )
        self.wd = self.scene_1.workingdir

        assign_perm('view_scene', self.user_a, self.scene_1)
        assign_perm('add_scene', self.user_a, self.scene_1)
        assign_perm('change_scene', self.user_a, self.scene_1)
        assign_perm('delete_scene', self.user_a, self.scene_1)
        assign_perm('view_scene', self.user_a, self.scene_2)
        assign_perm('add_scene', self.user_a, self.scene_2)
        assign_perm('change_scene', self.user_a, self.scene_2)
        assign_perm('delete_scene', self.user_a, self.scene_2)

        # Add files mimicking export options.
        self.images = ['image.png', 'image.jpg', 'image.gif', 'image.jpeg']
        self.simulation = ['simulation/a.sim', 'simulation/b.sim']
        self.movies = ['movie_empty.mp4', 'movie_big.mp4', 'movie.mp5']
        self.export = ['export/export.something']

    def test_after_publishing_rights_are_revoked(self):
        self.assertEqual(self.scene_1.shared, 'p')
        self.assertTrue(self.user_a.has_perm('view_scene', self.scene_1))
        self.assertTrue(self.user_a.has_perm('add_scene', self.scene_1))
        self.assertTrue(self.user_a.has_perm('change_scene', self.scene_1))
        self.assertTrue(self.user_a.has_perm('delete_scene', self.scene_1))

        self.scene_1.publish_company(self.user_a)

        self.assertEqual(self.scene_1.shared, 'c')
        self.assertTrue(self.user_a.has_perm('view_scene', self.scene_1))
        self.assertTrue(self.user_a.has_perm('add_scene', self.scene_1))
        self.assertTrue(not self.user_a.has_perm('change_scene', self.scene_1))
        self.assertTrue(not self.user_a.has_perm('delete_scene', self.scene_1))

        self.scene_1.publish_world(self.user_a)

        self.assertEqual(self.scene_1.shared, 'w')
        self.assertTrue(self.user_a.has_perm('view_scene', self.scene_1))
        self.assertTrue(not self.user_a.has_perm('add_scene', self.scene_1))
        self.assertTrue(not self.user_a.has_perm('change_scene', self.scene_1))
        self.assertTrue(not self.user_a.has_perm('delete_scene', self.scene_1))

    def test_publish_company_and_publish_world(self):
        """
        Test if we can publish to company, and test if we can then publish
        to World (after publishing to company)
        """
        scenes = get_objects_for_user(
            self.user_a,
            "view_scene",
            Scene.objects.all(),
            accept_global_perms=False
        )

        self.assertEqual(len(get_objects_for_user(
            self.user_b,
            "view_scene",
            Scene.objects.all(),
            accept_global_perms=False
        )), 0)
        self.assertEqual(len(get_objects_for_user(
            self.user_c,
            "view_scene",
            Scene.objects.all(),
            accept_global_perms=False
        )), 0)

        # publish company
        scenes[0].publish_company(self.user_a)
        # should not publish as scene is in idle state
        scenes[1].publish_company(self.user_a)

        self.assertEqual(len(get_objects_for_user(
            self.user_b,
            "view_scene",
            Scene.objects.all(),
            accept_global_perms=False
        )), 1)
        self.assertEqual(len(get_objects_for_user(
            self.user_c,
            "view_scene",
            Scene.objects.all(),
            accept_global_perms=False
        )), 0)

        # publish world
        scenes[0].publish_world(self.user_a)
        # should not publish as scene is in idle state
        scenes[1].publish_world(self.user_a)

        self.assertEqual(len(get_objects_for_user(
            self.user_b,
            "view_scene",
            Scene.objects.all(),
            accept_global_perms=False
        )), 1)
        self.assertEqual(len(get_objects_for_user(
            self.user_c,
            "view_scene",
            Scene.objects.all(),
            accept_global_perms=False
        )), 1)

    def test_publish_world(self):
        """
        Test if we can publish to world (before publishing to dtcompany)
        """
        scenes = get_objects_for_user(
            self.user_a,
            "view_scene",
            Scene.objects.all(),
            accept_global_perms=False
        )

        self.assertEqual(len(get_objects_for_user(
            self.user_b,
            "view_scene",
            Scene.objects.all(),
            accept_global_perms=False
        )), 0)
        self.assertEqual(len(get_objects_for_user(
            self.user_c,
            "view_scene",
            Scene.objects.all(),
            accept_global_perms=False
        )), 0)

        # publish world
        scenes[0].publish_world(self.user_a)
        # should not publish as scene is in idle state
        scenes[1].publish_world(self.user_a)

        self.assertEqual(len(get_objects_for_user(
            self.user_b,
            "view_scene",
            Scene.objects.all(),
            accept_global_perms=False
        )), 1)
        self.assertEqual(len(get_objects_for_user(
            self.user_c,
            "view_scene",
            Scene.objects.all(),
            accept_global_perms=False
        )), 1)

    def test_start_scene(self):
        started_date = None

        # a scene should only start when it's idle: check for each phase
        for phase in self.scene_1.phases:

            #  shift scene to phase
            self.scene_1.shift_to_phase(phase[0])

            # start scene
            self.scene_1.start()

            # check that phase is unshifted unless Idle: then it becomes started
            self.assertEqual(
                self.scene_1.phase,
                self.scene_1.phases.sim_start if (
                    phase[0] == self.scene_1.phases.idle) else phase[0]
            )

            # check date_started is untouched unless started from Idle state
            if phase[0] < self.scene_1.phases.idle:

                self.assertEqual(self.scene_1.date_started, started_date)

            if phase[0] == self.scene_1.phases.idle:

                self.assertTrue(self.scene_1.date_started <= now())
                started_date = self.scene_1.date_started  # store started date

            else:

                self.assertEqual(self.scene_1.date_started, started_date)

    def test_abort_scene(self):

        # abort is more complex
        for phase in self.scene_1.phases:

            #  shift scene to phase
            self.scene_1.shift_to_phase(phase[0])

            # abort scene
            self.scene_1.abort()

            # if the phase is after simulation start and before stopped
            if (phase[0] >= self.scene_1.phases.sim_start) and (
                    phase[0] <= self.scene_1.phases.sim_fin):
                # check that phase is shifted to stopped
                self.assertEqual(self.scene_1.phase,
                                 self.scene_1.phases.sim_fin)

            else:
                # check the abort is ignored
                self.assertEqual(self.scene_1.phase, phase[0])

    def test_reset_scene(self):
        date_started = now()
        progress = 10

        # a scene should only start when it's idle: check for each phase
        for phase in self.scene_1.phases:

            #  shift scene to phase
            self.scene_1.date_started = date_started
            self.scene_1.progress = progress
            self.scene_1.shift_to_phase(phase[0])

            # start scene
            self.scene_1.reset()

            # check that phase is unshifted unless Finished: then it becomes New
            self.assertEqual(
                self.scene_1.phase,
                self.scene_1.phases.new if (
                    phase[0] == self.scene_1.phases.fin) else phase[0]
            )

            # check properties are untouched unless reset from finished state
            if phase[0] == self.scene_1.phases.fin:
                self.assertEqual(self.scene_1.date_started, None)
                self.assertEqual(self.scene_1.progress, 0)
                self.assertEqual(self.scene_1.phase, self.scene_1.phases.new)

            else:
                self.assertEqual(self.scene_1.date_started, date_started)
                self.assertEqual(self.scene_1.progress, progress)
                self.assertEqual(self.scene_1.phase, phase[0])


class ScenarioZeroPhaseTestCase(TestCase):

    def test_phase_00(self):
        self.template = Template.objects.create(name="Template parent")
        self.scenario = Scenario.objects.create(name='Scenario parent', template=self.template)
        scene = Scene.objects.create(name='scene 1')
        scene.scenario = [self.scenario]

        scene.phase = scene.phases.new
        scene.update_and_phase_shift()

        # Even if multiple tasks run new or scene is
        # put into new again, only one workflow is created
        scene.phase = scene.phases.new
        scene.update_and_phase_shift()

        self.assertEqual(scene.phase, scene.phases.idle)
        self.assertEqual(scene.workflow.desired_state, 'non-existent')
        self.assertEqual(scene.workflow.cluster_state, 'non-existent')


class ScenarioPhasesTestCase(TestCase):
    """TODO Some sort of flow matrix should be defined between phases.
    We can then randomly set workflow states, and check whether the
    resulting phases are allowed. This is way too verbose.

    Basicly we create a framework for phases and check its function,
    not (what we're doing now) checking for each phase if changes are correct."""

    def setUp(self):
        self.template = Template.objects.create(name="Template parent")
        self.scenario = Scenario.objects.create(name='Scenario parent', template=self.template)
        self.scene_1 = Scene.objects.create(name='scene 1')
        self.scene_1.scenario = [self.scenario]
        self.scene_1.update_and_phase_shift()
        self.scene_2 = Scene.objects.create(name='scene 2')
        self.scene_2.scenario = [self.scenario]
        self.scene_2.update_and_phase_shift()
        self.scene_3 = Scene.objects.create(name='scene 3')
        self.scene_3.scenario = [self.scenario]
        self.scene_3.update_and_phase_shift()
        self.scene_4 = Scene.objects.create(name='scene 4')
        self.scene_4.scenario = [self.scenario]
        self.scene_4.update_and_phase_shift()

        self.p = self.scene_1.phases  # shorthand
        self.w = self.scene_1.entrypoints

    def test_phase_new(self):
        self.scene_1.phase = self.p.new

        self.scene_1.update_and_phase_shift()
        self.assertEqual(self.scene_1.phase, self.p.idle)

        # check if scene remains in phase 1 when not all workflows are created
        # check if scene moved to phase 2 when all workflows are created

    def test_phase_idle(self):
        self.scene_1.phase = self.p.idle

        self.scene_1.update_and_phase_shift()
        self.assertEqual(self.scene_1.phase, self.p.idle)

    def test_phase_sim_start(self):
        self.scene_1.phase = self.p.sim_start

        self.scene_1.update_and_phase_shift()
        self.assertEqual(self.scene_1.phase, self.p.sim_run)

        self.scene_1.phase = self.p.sim_start
        self.scene_1.workflow.cluster_state = 'running'
        self.scene_1.workflow.save()

        self.scene_1.update_and_phase_shift()
        self.assertEqual(self.scene_1.phase, self.p.sim_run)

    def test_phase_sim_run(self):
        self.scene_1.phase = self.p.sim_run

        self.scene_1.update_and_phase_shift()
        self.assertEqual(self.scene_1.phase, self.p.sim_run)

        # check if _local_scan was called

        # check if the progress is updated
        self.scene_1.phase = self.p.sim_run
        workflow = self.scene_1.workflow
        workflow.cluster_state = 'failed'
        workflow.save()

        self.scene_1.update_and_phase_shift()
        self.assertEqual(self.scene_1.phase, self.p.sim_fin)

    def test_phase_sim_fin(self):
        self.scene_1.phase = self.p.sim_fin

        workflow = self.scene_1.workflow
        workflow.cluster_state = 'non-existent'
        workflow.save()

        self.scene_1.update_and_phase_shift()
        self.assertEqual(self.scene_1.phase, self.p.fin)


class WorkflowTestCase(TestCase):

    def setUp(self):

        self.run_argo_ps_dict = {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Workflow",
            "metadata": {
                "labels": {
                    "workflows.argoproj.io/phase": "Running"
                },
                "name": "delft3dgt-lftrz",
            }
        }

        self.fin_argo_ps_dict = {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Workflow",
            "metadata": {
                "labels": {
                    "workflows.argoproj.io/phase": "Succeeded"
                },
                "name": "delft3dgt-lftrz",
            }
        }

        self.fail_argo_ps_dict = {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Workflow",
            "metadata": {
                "labels": {
                    "workflows.argoproj.io/phase": "Failed"
                },
                "name": "delft3dgt-lftrz",
            }
        }

        self.template = Template.objects.create(name="template")
        self.scenario = Scenario.objects.create(name="parent", template=self.template)
        self.scene_1 = Scene.objects.create(name="some-long-name")
        self.scene_1.scenario = [self.scenario]

        yaml = """
        metadata:
          name: delft3dgt-1
        spec:
          entrypoint: delft3dgt-main
          arguments:
            parameters:
            - name: uuid
              value: "test-images-3"
        """
        self.template.yaml_template.save("dummy.yaml", ContentFile(yaml))

        self.workflow = Workflow.objects.create(
            scene=self.scene_1,
            desired_state='created',
            cluster_state='non-existent',
        )

    @patch('logging.warn', autospec=True)
    @patch('delft3dworker.models.AsyncResult', autospec=True)
    def test_update_task_result(self, MockedAsyncResult, mocked_warn_method):

        async_result = MockedAsyncResult.return_value

        # Set up: A previous task is not yet finished
        self.workflow.task_uuid = uuid.UUID(
            '6764743a-3d63-4444-8e7b-bc938bff7792')
        self.workflow.task_starttime = now()
        async_result.ready.return_value = False
        async_result.state = "STARTED"
        async_result.result = "dockerid", "None"
        async_result.successful.return_value = False
        # call method
        self.workflow.update_task_result()

        # one time check for ready, no get and the task id remains
        self.assertEqual(async_result.ready.call_count, 1)
        self.assertEqual(self.workflow.task_uuid, uuid.UUID(
            '6764743a-3d63-4444-8e7b-bc938bff7792'))

        # Time has passed, task should expire
        self.workflow.task_starttime = now() - timedelta(seconds=settings.TASK_EXPIRE_TIME * 2)
        self.workflow.update_task_result()
        self.assertEqual(self.workflow.task_uuid, None)

        # Set up: task is now finished with Failure
        self.workflow.task_uuid = uuid.UUID(
            '6764743a-3d63-4444-8e7b-bc938bff7792')
        self.workflow.task_starttime = now()
        async_result.ready.return_value = True
        async_result.result = (
            '01234567890abcdefghijklmnopqrstuvwxyz01234567890abcdefghijkl'
        ), 'ERror MesSAge'
        async_result.state = "FAILURE"

        # call method
        self.workflow.update_task_result()

        # check that warning is logged
        self.assertEqual(mocked_warn_method.call_count, 3)

        # Set up: task is now finished
        self.workflow.task_uuid = uuid.UUID(
            '6764743a-3d63-4444-8e7b-bc938bff7792')
        async_result.ready.return_value = True
        async_result.successful.return_value = True
        async_result.result = (
            '01234567890abcdefghijklmnopqrstuvwxyz01234567890abcdefghijkl'
        ), 'INFO:root:Time to finish 70.0, 10.0% completed,'
        async_result.state = "SUCCESS"

        # call method
        self.workflow.update_task_result()

        # second check for ready, now one get and the task id is set to
        # None
        self.assertIsNone(self.workflow.task_uuid)

    @patch('delft3dworker.models.AsyncResult', autospec=True)
    def test_update_progress(self, MockedAsyncResult):

        async_result = MockedAsyncResult.return_value

        # Set up: A previous task is not yet finished
        self.workflow.task_uuid = uuid.UUID(
            '6764743a-3d63-4444-8e7b-bc938bff7792')
        self.workflow.task_starttime = now()
        async_result.ready.return_value = True
        async_result.state = "SUCCESS"
        async_result.result = "dockerid", u"None"
        async_result.successful.return_value = True

        # call method
        self.workflow.update_task_result()

        # check progress changed
        self.assertEqual(self.workflow.progress, 0)

        # Set up: task is now finished
        self.workflow.task_uuid = uuid.UUID(
            '6764743a-3d63-4444-8e7b-bc938bff7792')
        async_result.ready.return_value = True
        async_result.successful.return_value = True
        async_result.result = (
            '01234567890abcdefghijklmnopqrstuvwxyz01234567890abcdefghijkl'
        ), u"""INFO:root:Time to finish 70.0, 22.2222222222% completed, time steps  left 7.0
INFO:root:Time to finish 60.0, 33.3333333333% completed, time steps  left 6.0
INFO:root:Time to finish 50.0, 44.4444444444% completed, time steps  left 5.0
INFO:root:Time to finish 40.0, 55.5555555556% completed, time steps  left 4.0"""
        async_result.state = "SUCCESS"

        # call method
        self.workflow.update_task_result()

        # check progress changed
        self.assertEqual(self.workflow.progress, 56.0)

    @patch('logging.error', autospec=True)
    def test_update_state_and_save(self, mocked_error_method):

        # This test will test the behavior of a workflow
        # when it receives snapshot

        self.workflow.sync_cluster_state(
            None)
        self.assertEqual(
            self.workflow.cluster_state, 'non-existent')

        self.workflow.sync_cluster_state(
            self.run_argo_ps_dict)
        self.assertEqual(
            self.workflow.cluster_state, 'running')

        self.workflow.sync_cluster_state(
            self.fin_argo_ps_dict)
        self.assertEqual(
            self.workflow.cluster_state, 'failed')

        self.workflow.sync_cluster_state(
            self.fin_argo_ps_dict)
        self.assertEqual(
            self.workflow.cluster_state, 'succeeded')

        self.assertEqual(
            mocked_error_method.call_count, 1)  # event is logged as an error!

    @patch('delft3dcontainermanager.tasks.do_argo_create.apply_async',
           autospec=True)
    def test_create_workflow(self, mocked_task):
        task_uuid = uuid.UUID('6764743a-3d63-4444-8e7b-bc938bff7792')

        result = Mock()
        mocked_task.return_value = result
        result.id = task_uuid

        # call method, check if do_docker_create is called once, uuid updates
        self.workflow.create_workflow()

        template_model = self.workflow.scene.scenario.first().template
        with open(template_model.yaml_template.path) as f:
            template = yaml.load(f)
        template["metadata"] = {"name": "{}".format(self.workflow.name)}
        template["spec"]["arguments"]["parameters"] = [{"name": "uuid", "value": self.scene_1.suid},
                                                       {"name": "s3bucket", "value": settings.BUCKETNAME},
                                                       {"name": "parameters", "value": json.dumps(self.scene_1.parameters)}]

        # create workflow
        mocked_task.assert_called_once_with(
            args=(template,),
            expires=settings.TASK_EXPIRE_TIME)
        self.assertEqual(self.workflow.task_uuid, task_uuid)

        # update workflow state, call method multiple times
        self.workflow.cluster_state = 'running'
        self.workflow.create_workflow()
        self.workflow.create_workflow()
        self.workflow.create_workflow()
        self.workflow.create_workflow()

        # all subsequent calls were ignored
        mocked_task.assert_called_once_with(
            args=(template,),
            expires=settings.TASK_EXPIRE_TIME)

    @patch('delft3dcontainermanager.tasks.do_argo_remove.apply_async',
           autospec=True)
    def test_remove_workflow(self, mocked_task):
        task_uuid = uuid.UUID('6764743a-3d63-4444-8e7b-bc938bff7792')

        self.workflow.desired_state = 'non-existent'
        self.workflow.cluster_state = 'running'

        result = Mock()
        result.id = task_uuid
        # result.get.return_value = docker_id
        mocked_task.return_value = result

        # call method, check if do_docker_stop is called once, uuid updates
        self.workflow.remove_workflow()
        mocked_task.assert_called_once_with(
            args=(self.workflow.name,), expires=settings.TASK_EXPIRE_TIME)
        self.assertEqual(self.workflow.task_uuid, task_uuid)

        # update workflow state, call method multiple times
        self.workflow.cluster_state = 'non-existent'
        self.workflow.remove_workflow()
        self.workflow.remove_workflow()
        self.workflow.remove_workflow()
        self.workflow.remove_workflow()

        # all subsequent calls were ignored
        mocked_task.assert_called_once_with(
            args=(self.workflow.name,), expires=settings.TASK_EXPIRE_TIME)

    @patch('delft3dcontainermanager.tasks.get_kube_log.apply_async',
           autospec=True)
    def test_update_log(self, mocked_task):
        task_uuid = uuid.UUID('6764743a-3d63-4444-8e7b-bc938bff7792')

        self.workflow.desired_state = 'running'
        self.workflow.cluster_state = 'running'

        result = Mock()
        result.id = task_uuid
        # result.get.return_value = docker_id
        mocked_task.return_value = result

        # call method, get_docker_log is called once, uuid updates
        self.workflow.update_log()
        mocked_task.assert_called_once_with(
            args=(self.workflow.name,), expires=settings.TASK_EXPIRE_TIME)
        self.assertEqual(self.workflow.task_uuid, task_uuid)

        # 'finish' task, call method, get_docker_log is called again
        self.workflow.task_uuid = None
        self.workflow.update_log()
        self.assertEqual(mocked_task.call_count, 2)

        # 'exit' workflow, call method, get_docker_log is not called again
        self.workflow.cluster_state = 'exited'
        self.workflow.update_log()
        self.assertEqual(mocked_task.call_count, 2)


class SearchFormTestCase(TestCase):

    def setUp(self):

        self.sections_a = """
        [
            {
                "name": "section1",
                "variables": [
                    {
                        "id": "var_1",
                        "name": "Var 1",
                        "type": "numeric",
                        "default": "0",
                        "validators": {
                            "required": true,
                            "min": -10,
                            "max": 1
                        }
                    }
                ]
            },
            {
                "name": "section2",
                "variables": [
                    {
                        "id": "var_2",
                        "name": "Var 2",
                        "type": "text",
                        "default": "moo",
                        "validators": {
                            "required": true
                        }
                    }
                ]
            },
            {
                "name": "section3",
                "variables": [
                    {
                        "id": "var 4",
                        "name": "Var 4",
                        "type": "numeric",
                        "default": "0",
                        "validators": {
                            "required": true,
                            "min": -1,
                            "max": 1
                        }
                    }
                ]
            }
        ]
        """

        self.sections_b = """
        [
            {
                "name": "section1",
                "variables": [
                    {
                        "id": "var_1",
                        "name": "Var 1",
                        "type": "numeric",
                        "default": "0",
                        "validators": {
                            "required": true,
                            "min": -1,
                            "max": 10
                        }
                    }
                ]
            },
            {
                "name": "section2",
                "variables": [
                    {
                        "id": "var_2",
                        "name": "Var 2",
                        "type": "text",
                        "default": "something else which is ignored",
                        "validators": {
                            "required": "also ignored"
                        }
                    },
                    {
                        "id": "var_3",
                        "name": "Var 3",
                        "type": "text",
                        "default": "moo",
                        "validators": {
                            "required": false
                        }
                    }
                ]
            },
            {
                "name": "section3",
                "variables": [
                    {
                        "id": "var 4",
                        "name": "Var 4",
                        "type": "text",
                        "default": "moo",
                        "validators": {
                            "required": false
                        }
                    }
                ]
            },
            {
                "name": "section4",
                "variables": [
                    {
                        "id": "var 5",
                        "name": "Var 5",
                        "type": "text",
                        "default": "moo",
                        "validators": {
                            "required": false
                        }
                    }
                ]
            }
        ]
        """

        self.templates_res = json.loads("""
            [
                {"name":"Template 1", "id":1},
                {"name":"Template 2", "id":2}
            ]
        """)

        self.sections_res = json.loads("""
        [
            {
                "name": "section1",
                "variables": [
                    {
                        "id": "var_1",
                        "name": "Var 1",
                        "type": "numeric",
                        "validators": {
                            "min": -10,
                            "max": 10
                        }
                    }
                ]
            },
            {
                "name": "section2",
                "variables": [
                    {
                        "id": "var_2",
                        "name": "Var 2",
                        "type": "text",
                        "validators": {
                        }
                    },
                    {
                        "id": "var_3",
                        "name": "Var 3",
                        "type": "text",
                        "validators": {
                        }
                    }
                ]
            },
            {
                "name": "section3",
                "variables": [
                    {
                        "id": "var 4",
                        "name": "Var 4",
                        "type": "numeric",
                        "validators": {
                            "min": -1,
                            "max": 1
                        }
                    }
                ]
            },
            {
                "name": "section4",
                "variables": [
                    {
                        "id": "var 5",
                        "name": "Var 5",
                        "type": "text",
                        "validators": {
                        }
                    }
                ]
            }
        ]
        """)

    # TODO: implement proper means to generate search form json

    # def test_search_form_builds_on_template_save(self):
    #     """
    #     Test if saving multiple templates creates and updates the search form.
    #     """

    #     template = Template.objects.create(
    #         name='Template 1',
    #         meta='{}',
    #         sections=self.sections_a,
    #     )

    #     # first template created non-existing search form
    #     searchforms = SearchForm.objects.filter(name='MAIN')
    #     self.assertEqual(len(searchforms), 1)

    #     template2 = Template.objects.create(
    #         name='Template 2',
    #         meta='{}',
    #         sections=self.sections_b,
    #     )

    #     # second template did not create an additional search form
    #     searchforms = SearchForm.objects.filter(name='MAIN')
    #     self.assertEqual(len(searchforms), 1)

    #     # all fields are as expected
    #     searchform = searchforms[0]
    #     self.assertEqual(
    #         searchform.templates,
    #         self.templates_res
    #     )
    #     self.assertEqual(
    #         searchform.sections,
    #         self.sections_res
    #     )
