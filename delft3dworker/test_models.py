from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.test import TestCase

from guardian.shortcuts import get_objects_for_user
from guardian.shortcuts import assign_perm

from delft3dworker.models import Scenario
from delft3dworker.models import Scene


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


class SceneTestCase(TestCase):

    def setUp(self):
        self.user_a = User.objects.create_user(username='A')
        self.user_b = User.objects.create_user(username='B')
        self.user_c = User.objects.create_user(username='C')

        company_w = Group.objects.create(name='access:world')
        company_w.user_set.add(self.user_a)
        company_w.user_set.add(self.user_b)
        company_w.user_set.add(self.user_c)
        company_x = Group.objects.create(name='access:org:Company X')
        company_x.user_set.add(self.user_a)
        company_x.user_set.add(self.user_b)
        company_y = Group.objects.create(name='access:org:Company Y')
        company_y.user_set.add(self.user_c)

        scene = Scene.objects.create(
            name='Scene',
            owner=self.user_a,
            shared='p',
        )
        assign_perm('view_scene', self.user_a, scene)
        assign_perm('change_scene', self.user_a, scene)
        assign_perm('delete_scene', self.user_a, scene)

        # Model general
        self.user_a.user_permissions.add(
            Permission.objects.get(codename='view_scene'))
        self.user_b.user_permissions.add(
            Permission.objects.get(codename='view_scene'))
        self.user_c.user_permissions.add(
            Permission.objects.get(codename='view_scene'))

    def test_after_publishing_more_can_see(self):
        scene = get_objects_for_user(
            self.user_a,
            "view_scene",
            Scene.objects.all(),
            accept_global_perms=False
        )[0]
        self.assertTrue(scene.publish_company(self.user_a))
        self.assertEqual(scene.shared, 'c')
        self.assertTrue(scene.publish_world(self.user_a))
        self.assertEqual(scene.shared, 'w')

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
        self.assertTrue(scene.publish_world(self.user_a))

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
        self.assertTrue(scene.publish_world(self.user_a))

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

    def test_no_controls_after_publishing_company(self):
        scene = get_objects_for_user(
            self.user_a,
            "view_scene",
            Scene.objects.all(),
            accept_global_perms=False
        )[0]

        self.assertTrue(scene.publish_company(self.user_a))
        self.assertEqual(
            scene.start(), {"info": "start skipped - scene pubished"})
        self.assertEqual(
            scene.abort(), {"info": "abort skipped - scene pubished"})
        self.assertEqual(
            scene.revoke(), {"info": "revoke skipped - scene pubished"})

    def test_no_controls_after_publishing_world(self):
        scene = get_objects_for_user(
            self.user_a,
            "view_scene",
            Scene.objects.all(),
            accept_global_perms=False
        )[0]

        self.assertTrue(scene.publish_world(self.user_a))
        self.assertEqual(
            scene.start(), {"info": "start skipped - scene pubished"})
        self.assertEqual(
            scene.abort(), {"info": "abort skipped - scene pubished"})
        self.assertEqual(
            scene.revoke(), {"info": "revoke skipped - scene pubished"})
