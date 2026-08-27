import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import init_db, query_db
from game.scoring import ScoringEngine

class TestScoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        from game.game_engine import GameEngine
        GameEngine.reset_event(full_reset=True)

    def test_normalize_answer(self):
        self.assertEqual(ScoringEngine.normalize_answer("  cat are ready  "), "CAT ARE READY")
        self.assertEqual(ScoringEngine.normalize_answer("42"), "42")

    def test_manual_score_adjust(self):
        team = query_db("SELECT * FROM teams WHERE team_number = 1", one=True)
        orig_score = team['score']
        ScoringEngine.manual_score_adjust(team['id'], 25, "Test adjustment")
        updated = query_db("SELECT * FROM teams WHERE id = ?", (team['id'],), one=True)
        self.assertEqual(updated['score'], orig_score + 25)

if __name__ == '__main__':
    unittest.main()
