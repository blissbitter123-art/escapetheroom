import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import init_db, query_db
from game.elimination import EliminationEngine
from game.leaderboard import LeaderboardEngine

class TestElimination(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        from game.game_engine import GameEngine
        GameEngine.reset_event(full_reset=True)

    def test_round_elimination_execution(self):
        LeaderboardEngine.update_leaderboard()
        res = EliminationEngine.execute_round_elimination(1, 40)
        self.assertEqual(res['survived_count'], 40)
        self.assertEqual(res['eliminated_count'], 10)

        # Verify database statuses
        active_cnt = query_db("SELECT COUNT(*) as cnt FROM teams WHERE status = 'ACTIVE'", one=True)['cnt']
        elim_cnt = query_db("SELECT COUNT(*) as cnt FROM teams WHERE status = 'ELIMINATED'", one=True)['cnt']
        self.assertEqual(active_cnt, 40)
        self.assertEqual(elim_cnt, 10)

if __name__ == '__main__':
    unittest.main()
