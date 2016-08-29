from __future__ import absolute_import

import json
import os
import uuid
import zipfile

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.test import TestCase

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


class ContainerTestCase(TestCase):

    def setUp(self):

        self.created_docker_ps_dict = {
            'Status': 'Created 4 minutes ago',
            'Id':
            '01234567890abcdefghijklmnopqrstuvwxyz01234567890abcdefghijkl'
        }

        self.up_docker_ps_dict = {
            'Status': 'Up 4 minutes',
            'Id':
            '01234567890abcdefghijklmnopqrstuvwxyz01234567890abcdefghijkl'
        }

        self.exited_docker_ps_dict = {
            'Status': 'Exited (0) 2 hours ago',
            'Id':
            'abcdefghijklmnopqrstuvwxyz01234567890abcdefghijklmnopqrstuvw'
        }

        self.error_docker_ps_dict = {
            'Status': 'nvkeirwtynvowi',
            'Id':
            'abcdefghijklmnopqrstuvwxyz01234567890abcdefghijklmnopqrstuvw'
        }

        self.scene = Scene.objects.create()

        self.container = Container.objects.create(
            scene=self.scene,
            container_type='preprocess',
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
        async_result.ready.return_value = False
        async_result.state = "STARTED"

        # call method
        self.container.update_task_result()

        # one time check for ready, no get and the task id remains
        self.assertEqual(async_result.ready.call_count, 1)
        self.assertEqual(async_result.get.call_count, 0)
        self.assertEqual(self.container.task_uuid, uuid.UUID(
            '6764743a-3d63-4444-8e7b-bc938bff7792'))

        # Set up: task is now finished with Failure
        async_result.ready.return_value = True
        async_result.get.return_value = (
            '01234567890abcdefghijklmnopqrstuvwxyz01234567890abcdefghijkl'
        ), 'ERror MesSAge'
        async_result.state = "FAILURE"

        # call method
        self.container.update_task_result()

        # check that warning is logged
        self.assertEqual(mocked_warn_method.call_count, 1)

        # Set up: task is now finished
        async_result.ready.return_value = True
        async_result.get.return_value = (
            '01234567890abcdefghijklmnopqrstuvwxyz01234567890abcdefghijkl'
        ), 'This is a log message.'
        async_result.state = "SUCCESS"

        # call method
        self.container.update_task_result()

        # second check for ready, now one get and the task id is set to
        # None
        self.assertEqual(async_result.ready.call_count, 2)
        self.assertEqual(async_result.get.call_count, 1)
        self.assertIsNone(self.container.task_uuid)
        self.assertEqual(
            self.container.docker_id,
            '01234567890abcdefghijklmnopqrstuvwxyz01234567890abcdefghijkl'
        )

    @patch('logging.error', autospec=True)
    def test_update_state_and_save(self, mocked_error_method):

        # This test will test the behavior of a Container
        # when it receives snapshot

        self.container._update_state_and_save(
            None)
        self.assertEqual(
            self.container.docker_state, 'non-existent')

        self.container._update_state_and_save(
            self.created_docker_ps_dict)
        self.assertEqual(
            self.container.docker_state, 'created')

        self.container._update_state_and_save(
            self.up_docker_ps_dict)
        self.assertEqual(
            self.container.docker_state, 'running')

        self.container._update_state_and_save(
            self.exited_docker_ps_dict)
        self.assertEqual(
            self.container.docker_state, 'exited')

        self.container._update_state_and_save(
            self.error_docker_ps_dict)
        self.assertEqual(
            self.container.docker_state, 'unknown')
        self.assertEqual(
            mocked_error_method.call_count, 1)  # event is logged as an error!

    @patch('delft3dcontainermanager.tasks.do_docker_create.delay',
           autospec=True)
    def test_create_container(self, mocked_task):
        task_uuid = uuid.UUID('6764743a-3d63-4444-8e7b-bc938bff7792')

        result = Mock()
        mocked_task.return_value = result
        result.id = task_uuid

        # call method, check if do_docker_create is called once, uuid updates
        self.container._create_container()
        mocked_task.assert_called_once_with(settings.PREPROCESS_IMAGE_NAME)
        self.assertEqual(self.container.task_uuid, task_uuid)

        # update container state, call method multiple times
        self.container.docker_state = 'created'
        self.container._create_container()
        self.container._create_container()
        self.container._create_container()
        self.container._create_container()

        # all subsequent calls were ignored
        mocked_task.assert_called_once_with(settings.PREPROCESS_IMAGE_NAME)

    @patch('delft3dcontainermanager.tasks.do_docker_start.delay',
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
        mocked_task.assert_called_once_with(docker_id)
        self.assertEqual(self.container.task_uuid, task_uuid)
        self.assertEqual(self.container.task_uuid, task_uuid)

        # update container state, call method multiple times
        self.container.docker_state = 'running'
        self.container._start_container()
        self.container._start_container()
        self.container._start_container()
        self.container._start_container()

        # all subsequent calls were ignored
        mocked_task.assert_called_once_with(docker_id)

    @patch('delft3dcontainermanager.tasks.do_docker_stop.delay',
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
        mocked_task.assert_called_once_with(docker_id)
        self.assertEqual(self.container.task_uuid, task_uuid)

        # update container state, call method multiple times
        self.container.docker_state = 'exited'
        self.container._stop_container()
        self.container._stop_container()
        self.container._stop_container()
        self.container._stop_container()

        # all subsequent calls were ignored
        mocked_task.assert_called_once_with(docker_id)

    @patch('delft3dcontainermanager.tasks.do_docker_remove.delay',
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
        mocked_task.assert_called_once_with(docker_id)
        self.assertEqual(self.container.task_uuid, task_uuid)

        # update container state, call method multiple times
        self.container.docker_state = 'non-existent'
        self.container._remove_container()
        self.container._remove_container()
        self.container._remove_container()
        self.container._remove_container()

        # all subsequent calls were ignored
        mocked_task.assert_called_once_with(docker_id)

    @patch('delft3dcontainermanager.tasks.get_docker_log.delay',
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
        mocked_task.assert_called_once_with(docker_id)
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
