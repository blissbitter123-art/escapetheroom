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

    def test_wager_locking_creates_no_submission(self):
        """Step 1 of the gamble flow must NOT submit an answer yet."""
        ch = query_db("SELECT * FROM challenges WHERE challenge_key = 'r3_c2_gamble'", one=True)
        team = query_db("SELECT * FROM teams WHERE team_number = 5", one=True)

        ok, msg = ScoringEngine.lock_wager(team['id'], ch['id'], 'RISK')
        self.assertTrue(ok)
        sub = query_db("SELECT * FROM submissions WHERE team_id = ? AND challenge_id = ?",
                       (team['id'], ch['id']), one=True)
        self.assertIsNone(sub, "Locking a wager must not create a submission.")

    def test_wager_answer_scoring(self):
        """Step 2: after locking a wager, answering correctly applies the multiplier."""
        ch = query_db("SELECT * FROM challenges WHERE challenge_key = 'r3_c2_gamble'", one=True)
        team = query_db("SELECT * FROM teams WHERE team_number = 7", one=True)

        ok, _ = ScoringEngine.lock_wager(team['id'], ch['id'], 'ALL_IN')
        self.assertTrue(ok)

        orig_score = query_db("SELECT score FROM teams WHERE id = ?", (team['id'],), one=True)['score']
        is_corr, pts, msg = ScoringEngine.evaluate_submission(team['id'], ch['id'], ch['correct_answer'], 5000)
        self.assertTrue(is_corr)
        self.assertEqual(pts, ch['base_points'] * 3)
        updated = query_db("SELECT score FROM teams WHERE id = ?", (team['id'],), one=True)['score']
        self.assertEqual(updated, orig_score + pts)

    def test_wager_wrong_answer_penalty(self):
        """Wrong answer with RISK wager applies the -10 loss penalty."""
        ch = query_db("SELECT * FROM challenges WHERE challenge_key = 'r3_c2_gamble'", one=True)
        team = query_db("SELECT * FROM teams WHERE team_number = 8", one=True)

        ok, _ = ScoringEngine.lock_wager(team['id'], ch['id'], 'RISK')
        self.assertTrue(ok)

        is_corr, pts, msg = ScoringEngine.evaluate_submission(team['id'], ch['id'], "WRONG", 9000)
        self.assertFalse(is_corr)
        self.assertEqual(pts, -10)

    def test_hints_seeded_for_round3(self):
        """Round 3 hints ship with the challenges (managed via host Challenges edit)."""
        ch = query_db("SELECT * FROM challenges WHERE challenge_key = 'r3_c2_gamble'", one=True)
        lock = query_db("SELECT * FROM challenges WHERE challenge_key = 'r3_c1_lock_chain'", one=True)

        gamble_clues = query_db("SELECT * FROM challenge_clues WHERE challenge_id = ?", (ch['id'],))
        lock_clues = query_db("SELECT * FROM challenge_clues WHERE challenge_id = ?", (lock['id'],))
        self.assertGreaterEqual(len(gamble_clues), 1, "Round 3 gamble challenge must ship with hints.")
        self.assertGreaterEqual(len(lock_clues), 1, "Round 3 lock challenge must ship with hints.")

    def test_wager_locking_sets_team_column(self):
        """Locking wager must update team.round3_wager_type in database."""
        ch = query_db("SELECT * FROM challenges WHERE challenge_key = 'r3_c2_gamble'", one=True)
        team = query_db("SELECT * FROM teams WHERE team_number = 9", one=True)

        ok, msg = ScoringEngine.lock_wager(team['id'], ch['id'], 'ALL_IN')
        self.assertTrue(ok)
        updated_team = query_db("SELECT round3_wager_type FROM teams WHERE id = ?", (team['id'],), one=True)
        self.assertEqual(updated_team['round3_wager_type'], 'ALL_IN')

    def test_buy_hint_endpoint_and_persistence(self):
        """Buying a hint deducts points, records purchase, returns {success: true, hint: '...'} and persists."""
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True

        team = query_db("SELECT id, score FROM teams WHERE team_number = 10", one=True)
        ch = query_db("SELECT * FROM challenges WHERE challenge_key = 'r3_c2_gamble'", one=True)
        clue = query_db("SELECT * FROM challenge_clues WHERE challenge_id = ? ORDER BY order_index ASC", (ch['id'],), one=True)
        self.assertIsNotNone(clue)

        from database import execute_db
        # 1. With 0 score, purchase must be rejected with 400 (score cannot go negative)
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['team_id'] = team['id']

            fail_resp = client.post('/api/buy_hint', json={'challenge_id': ch['id'], 'clue_id': clue['id']})
            self.assertEqual(fail_resp.status_code, 400)
            fail_data = fail_resp.get_json()
            self.assertFalse(fail_data['success'])
            self.assertIn('Insufficient points', fail_data['error'])

            # 2. Give team enough points (e.g. 50 pts)
            execute_db("UPDATE teams SET score = 50 WHERE id = ?", (team['id'],))

            # 3. Purchase hint via POST /api/buy_hint
            resp = client.post('/api/buy_hint', json={'challenge_id': ch['id'], 'clue_id': clue['id']})
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertTrue(data['success'])
            self.assertEqual(data['hint'], clue['clue_text'])
            self.assertEqual(data['points_spent'], clue['cost_points'])

            # 4. Check score deducted properly from 50
            after_team = query_db("SELECT score FROM teams WHERE id = ?", (team['id'],), one=True)
            self.assertEqual(after_team['score'], 50 - clue['cost_points'])

            # 5. Check purchase recorded in database
            purchase = query_db("SELECT * FROM clue_purchases WHERE team_id = ? AND clue_id = ?",
                                (team['id'], clue['id']), one=True)
            self.assertIsNotNone(purchase)

            # 4. Check state endpoint returns purchased_hints / purchased_clues
            from game.round_manager import RoundManager
            RoundManager.set_active_challenge(ch['id'])
            state_resp = client.get('/api/state')
            self.assertEqual(state_resp.status_code, 200)
            st = state_resp.get_json()
            self.assertIn('purchased_clues', st)
            self.assertTrue(any(c['clue_id'] == clue['id'] for c in st['purchased_clues']))
            self.assertIn(clue['clue_text'], st.get('purchased_hints', []))

            # 5. Purchasing again returns the hint without double deducting points
            score_before_repeat = after_team['score']
            repeat_resp = client.post('/api/buy_hint', json={'challenge_id': ch['id'], 'clue_id': clue['id']})
            self.assertEqual(repeat_resp.status_code, 200)
            rep_data = repeat_resp.get_json()
            self.assertTrue(rep_data['success'])
            self.assertEqual(rep_data['hint'], clue['clue_text'])
            score_after_repeat = query_db("SELECT score FROM teams WHERE id = ?", (team['id'],), one=True)['score']
            self.assertEqual(score_after_repeat, score_before_repeat)

if __name__ == '__main__':
    unittest.main()
