import unittest

from sate_adequacy.scenario_catalog import all_scenario_ids
from sate_adequacy.scenario_runner import run_scenario_suite


class ScenarioRunnerTests(unittest.TestCase):
    def test_suite_green_and_covers_catalog(self) -> None:
        result = run_scenario_suite()
        export = result.export()
        self.assertTrue(result.green, export)
        self.assertGreaterEqual(int(export["executable"]), 12)
        seen = {item.scenario_id for item in result.outcomes}
        self.assertEqual(seen, set(all_scenario_ids()))


if __name__ == "__main__":
    unittest.main()
