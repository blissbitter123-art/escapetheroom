import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import init_db, query_db
from game.game_engine import GameEngine
from game.scoring import ScoringEngine

class TestRound3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        GameEngine.reset_event(full_reset=True)

    def test_wager_selection(self):
        ch = query_db("SELECT * FROM challenges WHERE challenge_key = 'r3_c2_gamble'", one=True)
        team = query_db("SELECT * FROM teams WHERE team_number = 6", one=True)

        ScoringEngine.evaluate_submission(team['id'], ch['id'], "ALL_IN", 3000)
        wager = query_db("SELECT * FROM wagers WHERE team_id = ?", (team['id'],), one=True)
        self.assertIsNotNone(wager)
        self.assertEqual(wager['wager_type'], 'ALL_IN')
        self.assertEqual(wager['multiplier'], 3.0)

if __name__ == '__main__':
    unittest.main()
