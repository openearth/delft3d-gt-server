from django.test import TestCase
from delft3dworker.models import Scenario


class ScenarioTestCase(TestCase):
    def setUp(self):
        Scenario.objects.create(name="Test single scene")
        Scenario.objects.create(name="Test multiple scenes")

    def test_scenario_parses_input(self):
        """Correctly parse scenario input"""

        # This should create only one scene
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

        # This should create 3 scenes
        multi_input = {
                "basinslope": {
                "group": "",
                "maxstep": 0.03,
                "minstep": 0.01,
                "stepinterval": 0.01,
                "units": "deg",
                "useautostep": True,
                "valid": True,
                "value": 0.0143
            },
        }

        scenario_single = Scenario.objects.get(name="Test single scene")
        scenario_multi = Scenario.objects.get(name="Test multiple scenes")

        scenario_single.load_settings(single_input)
        scenario_multi.load_settings(multi_input)

        self.assertEqual(len(scenario_single.scenes_parameters), 1)
        self.assertEqual(len(scenario_multi.scenes_parameters), 3)
