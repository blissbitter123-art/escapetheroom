import sys
import unittest
from app import create_app
from database import init_db, query_db
from game.game_engine import GameEngine
from game.round_manager import RoundManager
from game.leaderboard import LeaderboardEngine

class TestRound3EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        GameEngine.reset_event(full_reset=True)
        cls.app = create_app()
        cls.app.config['TESTING'] = True

    def test_full_round3_wager_and_hint_flow(self):
        client = self.app.test_client()

        # Step 1: Login as Team 1
        team = query_db("SELECT id, team_number, score, pin FROM teams WHERE team_number = 1", one=True)
        with client.session_transaction() as sess:
            sess['team_id'] = team['id']
            sess['team_number'] = team['team_number']

        # Advance to Round 3 and activate Stage B (r3_c2_gamble)
        RoundManager.advance_round(3)
        ch = query_db("SELECT * FROM challenges WHERE challenge_key = 'r3_c2_gamble'", one=True)
        self.assertIsNotNone(ch)
        RoundManager.set_active_challenge(ch['id'])
        RoundManager.set_phase('CHALLENGE')

        # Step 2: Check /team/home before wager lock (Selection Screen presented)
        resp = client.get('/team/home')
        html = resp.get_data(as_text=True)
        self.assertIn('SELECT YOUR RISK LEVEL', html)
        self.assertIn("submitWager('SAFE')", html)
        self.assertIn("submitWager('RISK')", html)
        self.assertIn("submitWager('ALL_IN')", html)

        # Step 3: Lock Wager via POST /team/wager
        wager_resp = client.post('/team/wager', json={'challenge_id': ch['id'], 'wager_type': 'ALL_IN'})
        self.assertEqual(wager_resp.status_code, 200)
        w_data = wager_resp.get_json()
        self.assertTrue(w_data['success'])

        # Verify database team.round3_wager_type
        updated_team = query_db("SELECT round3_wager_type FROM teams WHERE id = ?", (team['id'],), one=True)
        self.assertEqual(updated_team['round3_wager_type'], 'ALL_IN')

        # Step 4: Check /api/state shows team.round3_wager_type and team_wager
        st = client.get('/api/state').get_json()
        self.assertEqual(st['team']['round3_wager_type'], 'ALL_IN')
        self.assertIsNotNone(st['team_wager'])
        self.assertEqual(st['team_wager']['wager_type'], 'ALL_IN')

        # Check /team/home now shows Current Wager badge and Question
        resp_after_wager = client.get('/team/home')
        html_after_wager = resp_after_wager.get_data(as_text=True)
        self.assertIn('Current Wager:', html_after_wager)
        self.assertIn('ALL IN', html_after_wager)
        self.assertIn('hint-container', html_after_wager)

        # Step 5: Verify purchase rejected if team has insufficient points (e.g. 0 points)
        from database import execute_db
        fail_resp = client.post('/api/buy_hint', json={'challenge_id': ch['id']})
        self.assertEqual(fail_resp.status_code, 400)
        self.assertFalse(fail_resp.get_json()['success'])
        self.assertIn('Insufficient points', fail_resp.get_json()['error'])
        current_score = query_db("SELECT score FROM teams WHERE id = ?", (team['id'],), one=True)['score']
        self.assertEqual(current_score, 0)

        # Set team score to 30 points so they have enough points to afford the hint
        execute_db("UPDATE teams SET score = 30 WHERE id = ?", (team['id'],))
        score_before = 30

        # Now purchase hint via POST /api/buy_hint
        hint_resp = client.post('/api/buy_hint', json={'challenge_id': ch['id']})
        self.assertEqual(hint_resp.status_code, 200)
        h_data = hint_resp.get_json()
        self.assertTrue(h_data['success'])
        self.assertIn('hint', h_data)
        self.assertTrue(len(h_data['hint']) > 0)
        purchased_hint_text = h_data['hint']

        # Verify score deduction (30 - 10 = 20)
        score_after = query_db("SELECT score FROM teams WHERE id = ?", (team['id'],), one=True)['score']
        self.assertEqual(score_after, score_before - h_data['points_spent'])
        self.assertEqual(score_after, 20)

        # Step 6: Verify Page Refresh retains the revealed hint inside <div class="hint-container">
        import html as html_lib
        refresh_resp = client.get('/team/home')
        refresh_html = refresh_resp.get_data(as_text=True)
        self.assertIn('hint-container', refresh_html)
        self.assertIn(purchased_hint_text, html_lib.unescape(refresh_html))

        # Step 7: Answer question correctly and verify ALL_IN scoring (3x points)
        ans_resp = client.post('/team/submit', json={
            'challenge_id': ch['id'],
            'answer_text': ch['correct_answer'],
            'response_time_ms': 5000
        })
        self.assertEqual(ans_resp.status_code, 200)
        ans_data = ans_resp.get_json()
        self.assertTrue(ans_data['is_correct'])
        self.assertEqual(ans_data['points_awarded'], ch['base_points'] * 3)

        # Final score check
        final_team = query_db("SELECT score FROM teams WHERE id = ?", (team['id'],), one=True)
        self.assertEqual(final_team['score'], score_after + (ch['base_points'] * 3))

if __name__ == '__main__':
    unittest.main()
