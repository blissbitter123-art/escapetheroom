import unittest
import os
from database import init_db, query_db
from game.game_engine import GameEngine

class TestTeamManagement(unittest.TestCase):
    def setUp(self):
        init_db()
        GameEngine.reset_event(full_reset=True)

    def test_random_pin_seeding(self):
        teams = query_db("SELECT * FROM teams")
        self.assertEqual(len(teams), 50)
        pins = [t['pin'] for t in teams]
        # Check that PINs are string representations of numbers between 1000 and 9999
        for p in pins:
            self.assertTrue(p.isdigit())
            self.assertEqual(len(p), 4)

    def test_generate_teams(self):
        # Generate 10 custom teams
        GameEngine.generate_teams(10)
        teams = query_db("SELECT * FROM teams ORDER BY team_number ASC")
        self.assertEqual(len(teams), 10)
        self.assertEqual(teams[0]['team_name'], "Team 01")
        self.assertEqual(teams[9]['team_name'], "Team 10")

    def test_update_team_name(self):
        teams = query_db("SELECT * FROM teams ORDER BY team_number ASC")
        team_id = teams[0]['id']
        GameEngine.update_team_name(team_id, "The Survivors")
        updated = query_db("SELECT team_name FROM teams WHERE id = ?", (team_id,), one=True)
        self.assertEqual(updated['team_name'], "The Survivors")

if __name__ == '__main__':
    unittest.main()
