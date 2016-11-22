from __future__ import absolute_import

import json
import os
import uuid
import zipfile
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils.timezone import now

from guardian.shortcuts import assign_perm
from guardian.shortcuts import get_objects_for_user

from mock import Mock
from mock import patch

from delft3dworker.models import Scenario
from delft3dworker.models import Scene
from delft3dworker.models import Container
from delft3dworker.models import SearchForm
from delft3dworker.models import Template
from delft3dworker.models import User


class ScenarioTestCase(TestCase):

    def setUp(self):
        self.user_foo = User.objects.create_user(username='foo')

        self.scenario_single = Scenario.objects.create(
            name="Test single scene", owner=self.user_foo)
        self.scenario_multi = Scenario.objects.create(
            name="Test multiple scenes", owner=self.user_foo)
        self.scenario_A = Scenario.objects.create(
            name="Test hash A", owner=self.user_foo)
        self.scenario_B = Scenario.objects.create(
            name="Test hash B", owner=self.user_foo)

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

        self.scenario_multi = Scenario.objects.create(
            name="Test multiple scenes", owner=self.user_foo)
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
        self.scene = Scene.objects.create(
            name='Scene',
            owner=self.user_a,
            shared='p',
        )
        self.wd = self.scene.workingdir
        assign_perm('view_scene', self.user_a, self.scene)
        assign_perm('add_scene', self.user_a, self.scene)
        assign_perm('change_scene', self.user_a, self.scene)
        assign_perm('delete_scene', self.user_a, self.scene)

        # Add files mimicking export options.
        self.images = ['image.png', 'image.jpg', 'image.gif', 'image.jpeg']
        self.simulation = ['simulation/a.sim', 'simulation/b.sim']
        self.movies = ['movie_empty.mp4', 'movie_big.mp4', 'movie.mp5']
        self.export = ['export/export.something']

    @patch('delft3dcontainermanager.tasks.do_docker_create.apply_async',
           autospec=True)
    def test_versions(self, mocked_task):
        task_uuid = uuid.UUID('6764743a-3d63-4444-8e7b-bc938bff7792')

        result = Mock()
        mocked_task.return_value = result
        result.id = task_uuid

        self.assertDictEqual(self.scene.versions(), {})
        for i, container_type in enumerate(['preprocess', 'delft3d', 'process', 'postprocess', 'export', 'sync_cleanup']):
            container = Container(container_type=container_type)
            self.scene.container_set.add(container)
            name = container._create_container()
            version_dict = self.scene.versions()
            self.assertEqual(len(version_dict.keys()), i+1)
            if container_type == 'delft3d':
                self.assertIn('delft3d_version', version_dict[container_type])
                self.assertNotIn('REPOS_URL', version_dict[container_type])
                self.assertNotIn('SVN_REV', version_dict[container_type])
                self.assertEqual(version_dict[container_type]['delft3d_version'], settings.DELFT3D_VERSION)
            else:
                self.assertNotIn('delft3d_version', version_dict[container_type])
                self.assertIn('REPOS_URL', version_dict[container_type])
                self.assertIn('SVN_REV', version_dict[container_type])
                self.assertEqual(version_dict[container_type]['REPOS_URL'], settings.REPOS_URL)
                self.assertEqual(version_dict[container_type]['SVN_REV'], settings.SVN_REV)

    def test_after_publishing_rights_are_revoked(self):
        self.assertEqual(self.scene.shared, 'p')
        self.assertTrue(self.user_a.has_perm('view_scene', self.scene))
        self.assertTrue(self.user_a.has_perm('add_scene', self.scene))
        self.assertTrue(self.user_a.has_perm('change_scene', self.scene))
        self.assertTrue(self.user_a.has_perm('delete_scene', self.scene))

        self.scene.publish_company(self.user_a)

        self.assertEqual(self.scene.shared, 'c')
        self.assertTrue(self.user_a.has_perm('view_scene', self.scene))
        self.assertTrue(self.user_a.has_perm('add_scene', self.scene))
        self.assertTrue(not self.user_a.has_perm('change_scene', self.scene))
        self.assertTrue(not self.user_a.has_perm('delete_scene', self.scene))

        self.scene.publish_world(self.user_a)

        self.assertEqual(self.scene.shared, 'w')
        self.assertTrue(self.user_a.has_perm('view_scene', self.scene))
        self.assertTrue(not self.user_a.has_perm('add_scene', self.scene))
        self.assertTrue(not self.user_a.has_perm('change_scene', self.scene))
        self.assertTrue(not self.user_a.has_perm('delete_scene', self.scene))

    def test_publish_company_and_publish_world(self):
        """
        Test if we can publish to company, and test if we can then publish
        to World (after publishing to company)
        """
        scene = get_objects_for_user(
            self.user_a,
            "view_scene",
            Scene.objects.all(),
            accept_global_perms=False
        )[0]

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
        scene.publish_company(self.user_a)

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
        scene.publish_world(self.user_a)

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
        scene = get_objects_for_user(
            self.user_a,
            "view_scene",
            Scene.objects.all(),
            accept_global_perms=False
        )[0]

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
        scene.publish_world(self.user_a)

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

    # Broken: Models don't create directories anymore, so this test fails
    # TODO: Fix these tests
    # def test_export_images(self):
    #     # Mimick touch for creating empty files
    #     for f in self.images:
    #         open(os.path.join(os.getcwd(), self.wd, f), 'a').close()

    #     stream, fn = self.scene.export(['export_images'])
    #     zf = zipfile.ZipFile(stream)
    #     self.assertEqual(len(zf.namelist()), 3)

    # Broken: Models don't create directories anymore, so this test fails
    # TODO: Fix these tests
    # def test_export_sim(self):
    #     # Mimick touch for creating empty files
    #     for f in self.simulation:
    #         open(os.path.join(os.getcwd(), self.wd, f), 'a').close()
    #         # print(os.path.join(os.getcwd(), self.wd, f))
    #     stream, fn = self.scene.export(['export_input'])
    #     zf = zipfile.ZipFile(stream)
    #     self.assertEqual(len(zf.namelist()), 1)

    # Broken: Models don't create directories anymore, so this test fails
    # TODO: Fix these tests
    # def test_export_movies(self):
    #     # Mimick touch for creating empty files
    #     for f in self.movies:
    #         # Also make some data
    #         if 'big' in f:
    #            open(os.path.join(os.getcwd(), self.wd, f), 'a').write('TEST')
    #         else:
    #             open(os.path.join(os.getcwd(), self.wd, f), 'a').close()
    #         # print(os.path.join(os.getcwd(), self.wd, f))

    #     stream, fn = self.scene.export(['export_movie'])
    #     zf = zipfile.ZipFile(stream)
    #     self.assertEqual(len(zf.namelist()), 1)

    # Broken: Models don't create directories anymore, so this test fails
    # TODO: Fix these tests
    # def test_export_export(self):
    #     # Mimick touch for creating empty files
    #     for f in self.export:
    #         open(os.path.join(os.getcwd(), self.wd, f), 'a').close()

    #     stream, fn = self.scene.export(['export_thirdparty'])
    #     zf = zipfile.ZipFile(stream)
    #     self.assertEqual(len(zf.namelist()), 1)

    def test_start_scene(self):

        # TODO: write these tests

        pass

    def test_stop_scene(self):

        # TODO: write these tests

        pass


class ScenarioZeroPhaseTestCase(TestCase):

    def test_phase_00(self):
        scene = Scene.objects.create(name='scene')

        scene.phase = scene.phases.new
        scene.update_and_phase_shift()

        # Even if multiple tasks run new or scene is
        # put into new again, only one container is created
        scene.phase = scene.phases.new
        scene.update_and_phase_shift()

        self.assertEqual(scene.phase, scene.phases.preproc_create)

        self.assertEqual(
            len(scene.container_set.filter(container_type='preprocess')), 1)
        container = scene.container_set.get(container_type='preprocess')
        self.assertEqual(container.desired_state, 'non-existent')
        self.assertEqual(container.docker_state, 'non-existent')

        self.assertEqual(
            len(scene.container_set.filter(container_type='delft3d')), 1)
        container = scene.container_set.get(container_type='delft3d')
        self.assertEqual(container.desired_state, 'non-existent')
        self.assertEqual(container.docker_state, 'non-existent')

        self.assertEqual(
            len(scene.container_set.filter(container_type='process')), 1)
        container = scene.container_set.get(container_type='process')
        self.assertEqual(container.desired_state, 'non-existent')
        self.assertEqual(container.docker_state, 'non-existent')

        self.assertEqual(
            len(scene.container_set.filter(container_type='export')), 1)
        container = scene.container_set.get(container_type='export')
        self.assertEqual(container.desired_state, 'non-existent')
        self.assertEqual(container.docker_state, 'non-existent')


class ScenarioPhasesTestCase(TestCase):
    """TODO Some sort of flow matrix should be defined between phases.
    We can then randomly set container states, and check whether the
    resulting phases are allowed. This is way too verbose.

    Basicly we create a framework for phases and check its function,
    not (what we're doing now) checking for each phase if changes are correct."""

    def setUp(self):
        self.scene = Scene.objects.create(name='scene')
        self.scene.update_and_phase_shift()
        self.p = self.scene.phases  # shorthand

    def test_phase_new(self):
        self.scene.phase = self.p.new

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.preproc_create)

        # check if scene remains in phase 1 when not all containers are created
        # check if scene moved to phase 2 when all containers are created

    def test_phase_preproc_create(self):
        self.scene.phase = self.p.preproc_create

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.preproc_create)

        # check to see if the preprocessing container is set to running as
        # desired state

        # check if scene moved to phase 4 when preprocessing container is
        # running

    def test_phase_preproc_start(self):
        self.scene.phase = self.p.preproc_start

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.preproc_create)

        self.scene.phase = self.p.preproc_start
        container = self.scene.container_set.get(container_type='preprocess')
        container.docker_state = 'running'
        container.save()

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.preproc_run)

    def test_phase_preproc_run(self):
        self.scene.phase = self.p.preproc_run

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.preproc_start)

        self.scene.phase = self.p.preproc_start
        container = self.scene.container_set.get(container_type='preprocess')
        container.docker_state = 'exited'
        container.save()

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.preproc_fin)

    def test_phase_preproc_fin(self):
        self.scene.phase = self.p.preproc_fin

        container = self.scene.container_set.get(container_type='preprocess')
        container.docker_state = 'exited'
        container.save()

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.preproc_fin)

        container = self.scene.container_set.get(container_type='preprocess')
        container.docker_state = 'non-existent'
        container.save()

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.idle)

    def test_phase_idle(self):
        self.scene.phase = self.p.idle

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.idle)

    def test_phase_sim_create(self):
        self.scene.phase = self.p.sim_create

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.sim_create)

    def test_phase_sim_start(self):
        self.scene.phase = self.p.sim_start

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.sim_create)

        self.scene.phase = self.p.sim_start
        container = self.scene.container_set.get(container_type='delft3d')
        container.docker_state = 'running'
        container.save()

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.sim_run)

    def test_phase_sim_run(self):
        self.scene.phase = self.p.sim_run

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.sim_create)

        # check if _local_scan was called

        # check if the progress is updated

        self.scene.phase = self.p.sim_run
        container = self.scene.container_set.get(container_type='delft3d')
        container.docker_state = 'exited'
        container.save()
        container = self.scene.container_set.get(container_type='process')
        container.docker_state = 'exited'
        container.save()

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.sim_last_proc)

    def test_phase_sim_fin(self):
        self.scene.phase = self.p.sim_fin

        container = self.scene.container_set.get(container_type='delft3d')
        container.docker_state = 'exited'
        container.save()
        container = self.scene.container_set.get(container_type='process')
        container.docker_state = 'exited'
        container.save()

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.sim_fin)

        container = self.scene.container_set.get(container_type='delft3d')
        container.docker_state = 'non-existent'
        container.save()
        container = self.scene.container_set.get(container_type='process')
        container.docker_state = 'non-existent'
        container.save()

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.postproc_create)

        # check if the progress is updated

    def test_phase_sim_stop(self):
        self.scene.phase = self.p.sim_stop

        container = self.scene.container_set.get(container_type='delft3d')
        container.docker_state = 'running'
        container.save()
        container = self.scene.container_set.get(container_type='process')
        container.docker_state = 'running'
        container.save()

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.sim_stop)

        # check if the simulation and processing containers are set to exited
        # as desired state

        # check if scene moved to phase 14 when simulation container is
        # exited

    def test_phase_postproc_create(self):
        # Started postprocessing
        self.scene.phase = self.p.postproc_create
        container = self.scene.container_set.get(container_type='postprocess')
        container.docker_state = 'created'
        container.save()

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.postproc_start)

    def test_phase_postproc_start(self):
        # Started postprocessing
        self.scene.phase = self.p.postproc_start
        container = self.scene.container_set.get(container_type='postprocess')
        container.docker_state = 'running'
        container.save()

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.postproc_run)

    def test_phase_postproc_run(self):
        self.scene.phase = self.p.postproc_run
        container = self.scene.container_set.get(container_type='postprocess')
        container.docker_state = 'exited'
        container.save()

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.postproc_fin)

    def test_phase_postproc_fin(self):
        # Finished postprocessing
        self.scene.phase = self.p.postproc_fin

        container = self.scene.container_set.get(container_type='postprocess')
        container.docker_state = 'exited'
        container.save()

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.postproc_fin)

        container = self.scene.container_set.get(container_type='postprocess')
        container.docker_state = 'non-existent'
        container.save()

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.exp_create)

    def test_phase_exp_create(self):
        self.scene.phase = self.p.exp_create

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.exp_create)

        # check if the export container is set to exited
        # as desired state

        # check if scene moved to phase 15 when export container is
        # running

    def test_phase_exp_start(self):
        self.scene.phase = self.p.exp_start

        # Moves back to create if non-existent
        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.exp_create)

        # But moves on if created
        self.scene.phase = self.p.exp_start
        container = self.scene.container_set.get(container_type='export')
        container.docker_state = 'running'
        container.save()

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.exp_run)

    def test_phase_exp_run(self):
        self.scene.phase = self.p.exp_run

        # Moves back to create if non-existent
        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.exp_create)

        # But stays in phase if running
        container = self.scene.container_set.get(container_type='export')
        container.docker_state = 'running'
        container.save()

        self.scene.phase = self.p.exp_start
        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.exp_run)

    def test_phase_exp_fin(self):
        self.scene.phase = self.p.exp_fin

        container = self.scene.container_set.get(container_type='export')
        container.docker_state = 'exited'
        container.save()

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.exp_fin)

        container = self.scene.container_set.get(container_type='export')
        container.docker_state = 'non-existent'
        container.save()

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.sync_create)

    def test_phase_sync_create(self):
        self.scene.phase = self.p.sync_create

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.sync_create)

        # check if all containers are set to non-existent
        # as desired state

    def test_phase_sync_start(self):
        self.scene.phase = self.p.sync_start

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.sync_create)

        self.scene.phase = self.p.sync_start
        container = self.scene.container_set.get(container_type='sync_cleanup')
        container.docker_state = 'running'
        container.save()

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.sync_run)

    def test_phase_sync_run(self):
        self.scene.phase = self.p.sync_run
        for container in self.scene.container_set.all():
            container.docker_state = 'exited'
            container.save()

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.sync_fin)

        # check if scene stays in phase 18 when not all containers are
        # exited

        # check if scene moves to phase 19 when all containers are
        # exited

    def test_phase_sync_fin(self):
        self.scene.phase = self.p.sync_fin

        container = self.scene.container_set.get(container_type='sync_cleanup')
        container.docker_state = 'exited'
        container.save()

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.sync_fin)

        container = self.scene.container_set.get(container_type='sync_cleanup')
        container.docker_state = 'non-existent'
        container.save()

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.fin)

    def test_phase_abort_start(self):
        self.scene.phase = self.p.abort_start

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.abort_run)

        # check if simulation and processing containers are set to exited
        # as desired state

    def test_phase_abort_run(self):
        self.scene.phase = self.p.abort_run

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.abort_run)

        # check if scene remains in phase 1001 when not all containers are
        # exited

        # check if scene moves to phase 1002 when all containers are
        # exited

    def test_phase_abort_fin(self):
        self.scene.phase = self.p.abort_fin

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.idle)

    def test_phase_queued(self):
        self.scene.phase = self.p.queued

        self.scene.update_and_phase_shift()
        self.assertEqual(self.scene.phase, self.p.sim_create)

        # check if scene stays in phase 1003 when there are too many
        # simulations already running


class ContainerTestCase(TestCase):

    def setUp(self):

        self.created_docker_ps_dict = {'State': {
            'Status': 'created',
            'Id':
            '01234567890abcdefghijklmnopqrstuvwxyz01234567890abcdefghijkl'
        }}

        self.up_docker_ps_dict = {'State': {
            'Status': 'running',
            'Id':
            '01234567890abcdefghijklmnopqrstuvwxyz01234567890abcdefghijkl'
        }}

        self.exited_docker_ps_dict = {'State': {
            'Status': 'exited',
            'Id':
            'abcdefghijklmnopqrstuvwxyz01234567890abcdefghijklmnopqrstuvw'
        }}

        self.error_docker_ps_dict = {'State': {
            'Status': 'nvkeirwtynvowi',
            'Id':
            'abcdefghijklmnopqrstuvwxyz01234567890abcdefghijklmnopqrstuvw'
        }}

        self.scene = Scene.objects.create()

        self.container = Container.objects.create(
            scene=self.scene,
            container_type='preprocess',
            desired_state='created',
            docker_state='non-existent',
        )
        self.delft3d_container = Container.objects.create(
            scene=self.scene,
            container_type='delft3d',
            desired_state='created',
            docker_state='non-existent',
        )

    @patch('logging.warn', autospec=True)
    @patch('delft3dworker.models.AsyncResult', autospec=True)
    def test_update_task_result(self, MockedAsyncResult, mocked_warn_method):

        async_result = MockedAsyncResult.return_value

        # Set up: A previous task is not yet finished
        self.container.task_uuid = uuid.UUID(
            '6764743a-3d63-4444-8e7b-bc938bff7792')
        self.container.task_starttime = now()
        async_result.ready.return_value = False
        async_result.state = "STARTED"
        async_result.result = "dockerid", "None"
        async_result.successful.return_value = False
        # call method
        self.container.update_task_result()

        # one time check for ready, no get and the task id remains
        self.assertEqual(async_result.ready.call_count, 1)
        self.assertEqual(self.container.task_uuid, uuid.UUID(
            '6764743a-3d63-4444-8e7b-bc938bff7792'))

        # Time has passed, task should expire
        self.container.task_starttime = now() - timedelta(seconds=settings.TASK_EXPIRE_TIME * 2)
        self.container.update_task_result()
        self.assertEqual(self.container.task_uuid, None)

        # Set up: task is now finished with Failure
        self.container.task_uuid = uuid.UUID(
            '6764743a-3d63-4444-8e7b-bc938bff7792')
        self.container.task_starttime = now()
        async_result.ready.return_value = True
        async_result.result = (
            '01234567890abcdefghijklmnopqrstuvwxyz01234567890abcdefghijkl'
        ), 'ERror MesSAge'
        async_result.state = "FAILURE"

        # call method
        self.container.update_task_result()

        # check that warning is logged
        self.assertEqual(mocked_warn_method.call_count, 3)

        # Set up: task is now finished
        self.container.task_uuid = uuid.UUID(
            '6764743a-3d63-4444-8e7b-bc938bff7792')
        async_result.ready.return_value = True
        async_result.successful.return_value = True
        async_result.result = (
            '01234567890abcdefghijklmnopqrstuvwxyz01234567890abcdefghijkl'
        ), 'INFO:root:Time to finish 70.0, 10.0% completed,'
        async_result.state = "SUCCESS"

        # call method
        self.container.update_task_result()

        # second check for ready, now one get and the task id is set to
        # None
        self.assertIsNone(self.container.task_uuid)
        self.assertEqual(
            self.container.docker_id,
            '01234567890abcdefghijklmnopqrstuvwxyz01234567890abcdefghijkl'
        )

    @patch('delft3dworker.models.AsyncResult', autospec=True)
    def test_update_progress(self, MockedAsyncResult):

        async_result = MockedAsyncResult.return_value

        # Set up: A previous task is not yet finished
        self.delft3d_container.task_uuid = uuid.UUID(
            '6764743a-3d63-4444-8e7b-bc938bff7792')
        self.delft3d_container.task_starttime = now()
        async_result.ready.return_value = True
        async_result.state = "SUCCESS"
        async_result.result = "dockerid", u"None"
        async_result.successful.return_value = True

        # call method
        self.delft3d_container.update_task_result()

        # check progress changed
        self.assertEqual(self.delft3d_container.container_progress, 0)

        # Set up: task is now finished
        self.delft3d_container.task_uuid = uuid.UUID(
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
        self.delft3d_container.update_task_result()

        # check progress changed
        self.assertEqual(self.delft3d_container.container_progress, 56.0)

    @patch('logging.error', autospec=True)
    def test_update_state_and_save(self, mocked_error_method):

        # This test will test the behavior of a Container
        # when it receives snapshot

        self.container.update_from_docker_snapshot(
            None)
        self.assertEqual(
            self.container.docker_state, 'non-existent')

        self.container.update_from_docker_snapshot(
            self.created_docker_ps_dict)
        self.assertEqual(
            self.container.docker_state, 'created')

        self.container.update_from_docker_snapshot(
            self.up_docker_ps_dict)
        self.assertEqual(
            self.container.docker_state, 'running')

        self.container.update_from_docker_snapshot(
            self.exited_docker_ps_dict)
        self.assertEqual(
            self.container.docker_state, 'exited')

        self.container.update_from_docker_snapshot(
            self.error_docker_ps_dict)
        self.assertEqual(
            self.container.docker_state, 'unknown')
        self.assertEqual(
            mocked_error_method.call_count, 1)  # event is logged as an error!

    @patch('delft3dcontainermanager.tasks.do_docker_create.apply_async',
           autospec=True)
    def test_create_container(self, mocked_task):
        task_uuid = uuid.UUID('6764743a-3d63-4444-8e7b-bc938bff7792')

        result = Mock()
        mocked_task.return_value = result
        result.id = task_uuid

        # call method, check if do_docker_create is called once, uuid updates
        name = self.container._create_container()

        mocked_task.assert_called_once_with(
            args=({'type': 'preprocess'}, {}),
            expires=settings.TASK_EXPIRE_TIME,
            kwargs={'command': '/data/run.sh /data/svn/scripts/'
                    'preprocess/preprocess.py',
                    'folders': ['test/{}/preprocess'.format(self.scene.suid),
                                'test/{}/simulation'.format(self.scene.suid)],
                    'memory_limit': '200m',
                    'image': 'dummy_preprocessing',
                    'environment': {'uuid': str(self.scene.suid),
                                    'folder': os.path.join(
                                        self.scene.workingdir, 'simulation'),
                                    'REPOS_URL': settings.REPOS_URL,
                                    'SVN_REV': settings.SVN_REV},
                    'name': name,
                    'volumes': [
                        'test/{}/simulation:/data/output:z'.format(
                            self.scene.suid),
                        'test/{}/preprocess:/data/input:ro'.format(
                            self.scene.suid)]}
        )
        self.assertEqual(self.container.task_uuid, task_uuid)

        # update container state, call method multiple times
        self.container.docker_state = 'created'
        self.container._create_container()
        self.container._create_container()
        self.container._create_container()
        self.container._create_container()

        # all subsequent calls were ignored
        mocked_task.assert_called_once_with(args=(
            {'type': 'preprocess'}, {},),
            kwargs={'command': '/data/run.sh /data/svn/scripts/'
                    'preprocess/preprocess.py',
                    'folders': ['test/{}/preprocess'.format(self.scene.suid),
                                'test/{}/simulation'.format(self.scene.suid)],
                    'memory_limit': '200m',
                    'image': 'dummy_preprocessing',
                    'environment': {'uuid': str(self.scene.suid),
                                    'folder': os.path.join(
                                        self.scene.workingdir, 'simulation'),
                                    'REPOS_URL': settings.REPOS_URL,
                                    'SVN_REV': settings.SVN_REV},
                    'name': name,
                    'volumes': [
                        'test/{}/simulation:/data/output:z'.format(
                            self.scene.suid),
                        'test/{}/preprocess:/data/input:ro'.format(
                            self.scene.suid
                        )]},
            expires=settings.TASK_EXPIRE_TIME
        )

    @patch('delft3dcontainermanager.tasks.do_docker_start.apply_async',
           autospec=True)
    def test_start_container(self, mocked_task):
        docker_id = '01234567890abcdefghijklmnopqrstuvwxyz01234567890abcdefghi'
        task_uuid = uuid.UUID('6764743a-3d63-4444-8e7b-bc938bff7792')

        self.container.desired_state = 'running'
        self.container.docker_state = 'created'
        self.container.docker_id = docker_id

        result = Mock()
        result.id = task_uuid
        result.get.return_value = docker_id
        mocked_task.return_value = result

        # call method, check if do_docker_start is called once, uuid updates
        self.container._start_container()
        mocked_task.assert_called_once_with(
            args=(docker_id,), expires=settings.TASK_EXPIRE_TIME)
        self.assertEqual(self.container.task_uuid, task_uuid)
        self.assertEqual(self.container.task_uuid, task_uuid)

        # update container state, call method multiple times
        self.container.docker_state = 'running'
        self.container._start_container()
        self.container._start_container()
        self.container._start_container()
        self.container._start_container()

        # all subsequent calls were ignored
        mocked_task.assert_called_once_with(
            args=(docker_id,), expires=settings.TASK_EXPIRE_TIME)

    @patch('delft3dcontainermanager.tasks.do_docker_stop.apply_async',
           autospec=True)
    def test_stop_container(self, mocked_task):
        docker_id = '01234567890abcdefghijklmnopqrstuvwxyz01234567890abcdefghi'
        task_uuid = uuid.UUID('6764743a-3d63-4444-8e7b-bc938bff7792')

        self.container.desired_state = 'exited'
        self.container.docker_state = 'running'
        self.container.docker_id = docker_id

        result = Mock()
        result.id = task_uuid
        result.get.return_value = docker_id
        mocked_task.return_value = result

        # call method, check if do_docker_stop is called once, uuid updates
        self.container._stop_container()
        mocked_task.assert_called_once_with(
            args=(docker_id,), expires=settings.TASK_EXPIRE_TIME)
        self.assertEqual(self.container.task_uuid, task_uuid)

        # update container state, call method multiple times
        self.container.docker_state = 'exited'
        self.container._stop_container()
        self.container._stop_container()
        self.container._stop_container()
        self.container._stop_container()

        # all subsequent calls were ignored
        mocked_task.assert_called_once_with(
            args=(docker_id,), expires=settings.TASK_EXPIRE_TIME)

    @patch('delft3dcontainermanager.tasks.do_docker_remove.apply_async',
           autospec=True)
    def test_remove_container(self, mocked_task):
        docker_id = '01234567890abcdefghijklmnopqrstuvwxyz01234567890abcdefghi'
        task_uuid = uuid.UUID('6764743a-3d63-4444-8e7b-bc938bff7792')

        self.container.desired_state = 'non-existent'
        self.container.docker_state = 'created'
        self.container.docker_id = docker_id

        result = Mock()
        result.id = task_uuid
        result.get.return_value = docker_id
        mocked_task.return_value = result

        # call method, check if do_docker_remove is called once, uuid updates
        self.container._remove_container()
        mocked_task.assert_called_once_with(
            args=(docker_id,), expires=settings.TASK_EXPIRE_TIME)
        self.assertEqual(self.container.task_uuid, task_uuid)

        # update container state, call method multiple times
        self.container.docker_state = 'non-existent'
        self.container._remove_container()
        self.container._remove_container()
        self.container._remove_container()
        self.container._remove_container()

        # all subsequent calls were ignored
        mocked_task.assert_called_once_with(
            args=(docker_id,), expires=settings.TASK_EXPIRE_TIME)

    @patch('delft3dcontainermanager.tasks.get_docker_log.apply_async',
           autospec=True)
    def test_update_log(self, mocked_task):
        docker_id = '01234567890abcdefghijklmnopqrstuvwxyz01234567890abcdefghi'
        task_uuid = uuid.UUID('6764743a-3d63-4444-8e7b-bc938bff7792')

        self.container.desired_state = 'running'
        self.container.docker_state = 'running'
        self.container.docker_id = docker_id

        result = Mock()
        result.id = task_uuid
        result.get.return_value = docker_id
        mocked_task.return_value = result

        # call method, get_docker_log is called once, uuid updates
        self.container._update_log()
        mocked_task.assert_called_once_with(
            args=(docker_id,), expires=settings.TASK_EXPIRE_TIME)
        self.assertEqual(self.container.task_uuid, task_uuid)

        # 'finish' task, call method, get_docker_log is called again
        self.container.task_uuid = None
        self.container._update_log()
        self.assertEqual(mocked_task.call_count, 2)

        # 'exit' container, call method, get_docker_log is not called again
        self.container.docker_state = 'exited'
        self.container._update_log()
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

    def test_search_form_builds_on_template_save(self):
        """
        Test if saving multiple templates creates and updates the search form.
        """

        template = Template.objects.create(
            name='Template 1',
            meta='{}',
            sections=self.sections_a,
        )

        # first template created non-existing search form
        searchforms = SearchForm.objects.filter(name='MAIN')
        self.assertEqual(len(searchforms), 1)

        template2 = Template.objects.create(
            name='Template 2',
            meta='{}',
            sections=self.sections_b,
        )

        # second template did not create an additional search form
        searchforms = SearchForm.objects.filter(name='MAIN')
        self.assertEqual(len(searchforms), 1)

        # all fields are as expected
        searchform = searchforms[0]
        self.assertEqual(
            searchform.templates,
            self.templates_res
        )
        self.assertEqual(
            searchform.sections,
            self.sections_res
        )
