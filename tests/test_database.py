import unittest
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import init_db, query_db, execute_db

class TestDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        from game.game_engine import GameEngine
        GameEngine.reset_event(full_reset=True)

    def test_tables_exist(self):
        tables = query_db("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = [t['name'] for t in tables]
        required_tables = ['event', 'rounds', 'teams', 'challenges', 'submissions', 'scores', 'eliminations', 'wagers', 'event_logs']
        for tbl in required_tables:
            self.assertIn(tbl, table_names)

    def test_team_insertion_and_query(self):
        team = query_db("SELECT * FROM teams WHERE team_number = 1", one=True)
        if not team:
            execute_db("INSERT INTO teams (team_number, team_name, pin) VALUES (99, 'Test Team 99', '9999')")
            team = query_db("SELECT * FROM teams WHERE team_number = 99", one=True)
        self.assertIsNotNone(team)

if __name__ == '__main__':
    unittest.main()
