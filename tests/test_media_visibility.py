import time
import unittest
from app import create_app
from database import init_db, query_db, execute_db
from game.round_manager import RoundManager
from game.timer_manager import TimerManager
from game.game_engine import GameEngine

class TestMediaVisibility(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            init_db()
            RoundManager.seed_initial_data()

    def test_start_timer_with_media_duration(self):
        with self.app.app_context():
            TimerManager.start_timer(duration_sec=45, media_visibility_sec=15)
            event = query_db("SELECT * FROM event WHERE id = 1", one=True)
            self.assertEqual(event['challenge_duration_sec'], 45)
            self.assertEqual(event['media_visibility_duration_sec'], 15)

            media_timer = TimerManager.get_media_timer()
            self.assertEqual(media_timer['visibility_duration'], 15)
            self.assertFalse(media_timer['is_expired'])
            self.assertGreaterEqual(media_timer['remaining'], 14)
            self.assertIsNotNone(media_timer['hide_at'])

    def test_host_control_start_challenge_payload(self):
        with self.client.session_transaction() as sess:
            sess['is_host'] = True

        # Launch challenge 1 with custom question duration 45 and media visibility duration 15
        payload = {
            "action": "start_challenge",
            "question_id": "r1c1",
            "duration": 45,
            "media_visibility_duration": 15
        }
        res = self.client.post('/api/host/control', json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))

        # Check /api/state returns both durations and timer objects
        state_res = self.client.get('/api/state')
        self.assertEqual(state_res.status_code, 200)
        state = state_res.get_json()

        self.assertEqual(state['timer']['total_duration'], 45)
        self.assertGreaterEqual(state['timer']['remaining'], 44)
        self.assertTrue(state['timer']['is_running'])

        self.assertEqual(state['media_visibility_duration'], 15)
        self.assertIsNotNone(state['media_hide_at'])
        self.assertIn('media_timer', state)
        self.assertEqual(state['media_timer']['visibility_duration'], 15)
        self.assertFalse(state['media_timer']['is_expired'])
        self.assertGreaterEqual(state['media_timer']['remaining'], 14)

    def test_mid_question_refresh_simulation(self):
        """At 10s elapsed of a 45s question with 15s media visibility:
        Media has 5s remaining, question has 35s remaining."""
        with self.app.app_context():
            start_time = time.time() - 10.0
            execute_db("""
                UPDATE event
                SET challenge_start_time = ?,
                    challenge_paused_at = NULL,
                    pause_accumulated_sec = 0,
                    challenge_duration_sec = 45,
                    media_visibility_duration_sec = 15,
                    status = 'ROUND_ACTIVE'
                WHERE id = 1
            """, (start_time,))

        state_res = self.client.get('/api/state')
        state = state_res.get_json()

        # Question timer: 45 - 10 = ~35
        self.assertIn(state['timer']['remaining'], (34, 35))
        self.assertTrue(state['timer']['is_running'])

        # Media timer: 15 - 10 = ~5
        self.assertIn(state['media_timer']['remaining'], (4, 5))
        self.assertFalse(state['media_timer']['is_expired'])

    def test_post_expiration_refresh_simulation(self):
        """At 20s elapsed of a 45s question with 15s media visibility:
        Media is expired (0s remaining, is_expired=True),
        while main question countdown continues running with 25s remaining."""
        with self.app.app_context():
            start_time = time.time() - 20.0
            execute_db("""
                UPDATE event
                SET challenge_start_time = ?,
                    challenge_paused_at = NULL,
                    pause_accumulated_sec = 0,
                    challenge_duration_sec = 45,
                    media_visibility_duration_sec = 15,
                    status = 'ROUND_ACTIVE'
                WHERE id = 1
            """, (start_time,))

        state_res = self.client.get('/api/state')
        state = state_res.get_json()

        # Question timer still running with ~25s left
        self.assertIn(state['timer']['remaining'], (24, 25))
        self.assertTrue(state['timer']['is_running'])

        # Media timer must be expired
        self.assertEqual(state['media_timer']['remaining'], 0)
        self.assertTrue(state['media_timer']['is_expired'])

    def test_pause_and_resume_preserves_both_timers(self):
        with self.app.app_context():
            start_time = time.time() - 5.0
            execute_db("""
                UPDATE event
                SET challenge_start_time = ?,
                    challenge_paused_at = NULL,
                    pause_accumulated_sec = 0,
                    challenge_duration_sec = 45,
                    media_visibility_duration_sec = 15,
                    status = 'ROUND_ACTIVE'
                WHERE id = 1
            """, (start_time,))

            # Pause timer
            TimerManager.pause_timer()
            media_timer = TimerManager.get_media_timer()
            # 15 - 5 = 10s remaining
            self.assertIn(media_timer['remaining'], (9, 10))
            self.assertFalse(media_timer['is_expired'])

            # Resume timer
            TimerManager.resume_timer()
            media_timer_after = TimerManager.get_media_timer()
            self.assertIn(media_timer_after['remaining'], (9, 10))
            self.assertFalse(media_timer_after['is_expired'])

if __name__ == '__main__':
    unittest.main()
