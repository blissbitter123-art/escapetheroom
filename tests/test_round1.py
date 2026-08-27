import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import init_db, query_db
from game.game_engine import GameEngine
from game.scoring import ScoringEngine

class TestRound1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        GameEngine.reset_event(full_reset=True)

    def test_speed_test_evaluation(self):
        ch = query_db("SELECT * FROM challenges WHERE challenge_key = 'r1_c1_speed_test'", one=True)
        self.assertIsNotNone(ch)
        team = query_db("SELECT * FROM teams WHERE team_number = 1", one=True)
        
        # Test correct answer "7"
        is_corr, pts, msg = ScoringEngine.evaluate_submission(team['id'], ch['id'], "7", 2000)
        self.assertTrue(is_corr)
        self.assertGreater(pts, 0)

    def test_no_submission_trap(self):
        ch = query_db("SELECT * FROM challenges WHERE challenge_key = 'r1_c3_trap'", one=True)
        self.assertIsNotNone(ch)
        team = query_db("SELECT * FROM teams WHERE team_number = 2", one=True)

        # Team submitting answer "10" triggers trap penalty!
        is_corr, pts, msg = ScoringEngine.evaluate_submission(team['id'], ch['id'], "10", 3000)
        self.assertFalse(is_corr)
        self.assertLess(pts, 0)

if __name__ == '__main__':
    unittest.main()
