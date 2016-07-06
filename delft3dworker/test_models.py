from django.test import TestCase
from delft3dworker.models import Scenario, User


class ScenarioTestCase(TestCase):
    def setUp(self):
        self.user_foo = User.objects.create(username='foo')

        self.scenario_single = Scenario.objects.create(name="Test single scene", owner=self.user_foo)
        self.scenario_multi = Scenario.objects.create(name="Test multiple scenes", owner=self.user_foo)
        self.scenario_A = Scenario.objects.create(name="Test hash A", owner=self.user_foo)
        self.scenario_B = Scenario.objects.create(name="Test hash B", owner=self.user_foo)

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
                    "values": [0.0143,0.0145,0.0146]
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
