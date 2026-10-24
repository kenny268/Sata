import unittest

from sate_adequacy.champion import ShadowMetrics, compare_champion_challenger


class ChampionTests(unittest.TestCase):
    def test_challenger_wins_on_rank_corr(self) -> None:
        champion = ShadowMetrics("c", rank_corr=0.1, signals_ingested=10, mean_shadow_c=0.2)
        challenger = ShadowMetrics("ch", rank_corr=0.3, signals_ingested=10, mean_shadow_c=0.2)
        verdict = compare_champion_challenger(champion, challenger)
        self.assertEqual(verdict.winner, "ch")
        self.assertTrue(verdict.promotion_params_frozen)


if __name__ == "__main__":
    unittest.main()
