import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from config import HOST_PASSWORD
from database import init_db, query_db

class TestChallengesAndAuth(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        init_db()

    def test_host_password(self):
        self.assertEqual(HOST_PASSWORD, 'apnakaamkr420')

    def test_host_login_with_new_password(self):
        # Attempt login with correct password
        response = self.client.post('/host/login', data={'password': 'apnakaamkr420'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Attempt login with wrong password
        response = self.client.post('/host/login', data={'password': 'wrongpassword'}, follow_redirects=True)
        self.assertIn(b'Invalid Host Password', response.data)

    def test_challenge_crud_api(self):
        # Log in as host first
        with self.client.session_transaction() as sess:
            sess['is_host'] = True

        # 1. Create a custom challenge
        create_payload = {
            'action': 'save_challenge',
            'challenge': {
                'challenge_key': 'test_r1_custom_99',
                'round_id': 1,
                'mission_id': 1,
                'title': 'Infinite Custom Challenge 99',
                'description': 'A custom challenge built dynamically.',
                'challenge_type': 'CUSTOM_PUZZLE',
                'duration_sec': 90,
                'correct_answer': 'INFINITE_POSSIBILITIES',
                'expected_action': 'SUBMIT_ANSWER',
                'base_points': 50,
                'speed_bonus_points': 25,
                'penalty_points': 10,
                'difficulty': 'MONSTER',
                'display_data_json': '{"prompt": "Solve infinite possibilities"}',
                'options_json': '["Possibility 1", "Possibility 2"]',
                'order_index': 99
            }
        }
        res = self.client.post('/api/host/control', json=create_payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        ch_id = data['challenge_id']

        # 2. Get the challenge details
        res_get = self.client.post('/api/host/control', json={'action': 'get_challenge', 'challenge_id': ch_id})
        self.assertEqual(res_get.status_code, 200)
        ch_data = res_get.get_json()['challenge']
        self.assertEqual(ch_data['title'], 'Infinite Custom Challenge 99')
        self.assertEqual(ch_data['correct_answer'], 'INFINITE_POSSIBILITIES')

        # 3. Update the challenge
        create_payload['challenge']['id'] = ch_id
        create_payload['challenge']['title'] = 'Updated Infinite Challenge 99'
        res_update = self.client.post('/api/host/control', json=create_payload)
        self.assertTrue(res_update.get_json()['success'])

        updated_ch = query_db("SELECT * FROM challenges WHERE id = ?", (ch_id,), one=True)
        self.assertEqual(updated_ch['title'], 'Updated Infinite Challenge 99')

        # 4. Delete the challenge
        res_del = self.client.post('/api/host/control', json={'action': 'delete_challenge', 'challenge_id': ch_id})
        self.assertTrue(res_del.get_json()['success'])
        deleted_ch = query_db("SELECT * FROM challenges WHERE id = ?", (ch_id,), one=True)
        self.assertIsNone(deleted_ch)

if __name__ == '__main__':
    unittest.main()
