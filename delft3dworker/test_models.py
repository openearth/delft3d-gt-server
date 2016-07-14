from __future__ import absolute_import

import json
from mock import patch
import os
import zipfile


from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.test import TestCase

from guardian.shortcuts import assign_perm
from guardian.shortcuts import get_objects_for_user

from delft3dworker.models import Scenario
from delft3dworker.models import Scene
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
        self.assertTrue(mocked_scene_method.call_count, 3)

    @patch('delft3dworker.models.Scene.abort', autospec=True)
    def test_abort(self, mocked_scene_method):
        """
        Test if scenes are aborted when scenario is aborted
        """
        self.scenario_multi.abort(self.user_foo)
        self.assertTrue(mocked_scene_method.call_count, 3)

    @patch('delft3dworker.models.Scene.delete', autospec=True)
    def test_delete(self, mocked_scene_method):
        """
        Test if scenes are deleted when scenario is deleted
        """
        self.scenario_multi.delete(self.user_foo)
        self.assertTrue(mocked_scene_method.call_count, 3)

    @patch('delft3dworker.models.Scene.publish_company', autospec=True)
    def test_publish_company(self, mocked_scene_method):
        """
        Test if scenes are published to company when scenario is published
        to company
        """
        self.scenario_multi.publish_company(self.user_foo)
        self.assertTrue(mocked_scene_method.call_count, 3)

    @patch('delft3dworker.models.Scene.publish_world', autospec=True)
    def test_publish_world(self, mocked_scene_method):
        """
        Test if scenes are published to world when scenario is published
        to world
        """
        self.scenario_multi.publish_world(self.user_foo)
        self.assertTrue(mocked_scene_method.call_count, 3)


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

    def test_after_publishing_more_can_see(self):
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
        self.assertTrue(scene.publish_company(self.user_a))

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

    def test_after_publishing_more_can_see(self):
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

    def test_export_images(self):
        # Mimick touch for creating empty files
        for f in self.images:
            open(os.path.join(os.getcwd(), self.wd, f), 'a').close()

        stream, fn = self.scene.export(['export_images'])
        zf = zipfile.ZipFile(stream)
        self.assertEqual(len(zf.namelist()), 3)

    def test_export_sim(self):
        # Mimick touch for creating empty files
        for f in self.simulation:
            open(os.path.join(os.getcwd(), self.wd, f), 'a').close()
            # print(os.path.join(os.getcwd(), self.wd, f))
        stream, fn = self.scene.export(['export_input'])
        zf = zipfile.ZipFile(stream)
        self.assertEqual(len(zf.namelist()), 1)

    def test_export_movies(self):
        # Mimick touch for creating empty files
        for f in self.movies:
            # Also make some data
            if 'big' in f:
                open(os.path.join(os.getcwd(), self.wd, f), 'a').write('TEST')
            else:
                open(os.path.join(os.getcwd(), self.wd, f), 'a').close()
            # print(os.path.join(os.getcwd(), self.wd, f))

        stream, fn = self.scene.export(['export_movie'])
        zf = zipfile.ZipFile(stream)
        self.assertEqual(len(zf.namelist()), 1)

    def test_export_export(self):
        # Mimick touch for creating empty files
        for f in self.export:
            open(os.path.join(os.getcwd(), self.wd, f), 'a').close()

        stream, fn = self.scene.export(['export_thirdparty'])
        zf = zipfile.ZipFile(stream)
        self.assertEqual(len(zf.namelist()), 1)

    @patch('delft3dworker.tasks.chainedtask.delay', autospec=True)
    def test_start_scene(self, mocked_chainedtask):
        # mockchainedtask.return_value = {"info": {}, 'id': '22', 'state': ""}
        mocked_chainedtask.return_value.task_id = '22'
        mocked_chainedtask.return_value.state = "PROCESSING"

        started = self.scene.start()

    @patch('delft3dworker.models.revoke_task', autospec=True)
    @patch('celery.contrib.abortable.AbortableAsyncResult', autospec=True)
    def test_stop_scene(self, mocked_task_delay, mocked_abortable_result):
        mocked_task_delay.return_value = {"info": {}, 'id': '22', 'state': ""}
        self.scene.state = "PROCESSING"
        aborted = self.scene.abort()

        self.scene.state = "BUSY"
        revoked = self.scene.abort()


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
