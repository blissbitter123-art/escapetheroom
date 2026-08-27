import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import init_db, query_db
from game.game_engine import GameEngine
from game.scoring import ScoringEngine

class TestRound2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        GameEngine.reset_event(full_reset=True)

    def test_host_story_cipher(self):
        ch = query_db("SELECT * FROM challenges WHERE challenge_key = 'r2_c1_host_story'", one=True)
        team = query_db("SELECT * FROM teams WHERE team_number = 3", one=True)
        is_corr, pts, msg = ScoringEngine.evaluate_submission(team['id'], ch['id'], "9-3-4-2", 4000)
        self.assertTrue(is_corr)

    def test_double_agent_choices(self):
        ch = query_db("SELECT * FROM challenges WHERE challenge_key = 'r2_c5_double_agent'", one=True)
        t1 = query_db("SELECT * FROM teams WHERE team_number = 4", one=True)
        t2 = query_db("SELECT * FROM teams WHERE team_number = 5", one=True)

        # Misunderstood clue (Safe option: +10)
        _, pts_safe, _ = ScoringEngine.evaluate_submission(t1['id'], ch['id'], "Misunderstood clue", 2000)
        self.assertEqual(pts_safe, 10)

        # Wrong risk choice (-10 penalty)
        _, pts_wrong, _ = ScoringEngine.evaluate_submission(t2['id'], ch['id'], "Projector lied", 2000)
        self.assertEqual(pts_wrong, -10)

if __name__ == '__main__':
    unittest.main()
