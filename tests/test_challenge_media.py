import unittest
import os
import sys
import uuid
import base64
import io

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from database import init_db, query_db, execute_db
from game.round_manager import RoundManager

TINY_PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
)


class TestChallengeMediaAndHostTeams(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        init_db()
        with self.client.session_transaction() as sess:
            sess['is_host'] = True

    def _create_test_challenge(self):
        key = f"test_media_{uuid.uuid4().hex[:8]}"
        res = self.client.post('/api/host/control', json={
            'action': 'save_challenge',
            'challenge': {
                'challenge_key': key,
                'round_id': 1,
                'title': 'Media Test Challenge',
                'description': 'Challenge used to verify media display.',
                'challenge_type': 'CUSTOM_PUZZLE',
                'duration_sec': 60,
                'correct_answer': 'ANY',
                'expected_action': 'SUBMIT_ANSWER',
                'order_index': 999
            }
        })
        data = res.get_json()
        self.assertTrue(data['success'], f"save_challenge failed: {data}")
        return data['challenge_id']

    def _save_event_state(self):
        ev = query_db("SELECT * FROM event WHERE id = 1", one=True)
        return {k: ev[k] for k in ('current_round', 'current_challenge_id', 'current_phase', 'status')}

    def _restore_event_state(self, saved):
        execute_db(
            "UPDATE event SET current_round = ?, current_challenge_id = ?, current_phase = ?, status = ? WHERE id = 1",
            (saved['current_round'], saved['current_challenge_id'], saved['current_phase'], saved['status'])
        )

    def test_upload_media_with_required_seconds(self):
        ch_id = self._create_test_challenge()
        saved_event = self._save_event_state()
        try:
            RoundManager.set_active_challenge(ch_id)

            # 1. Upload an image with a required display duration of 25 seconds
            res = self.client.post('/api/upload_media', data={
                'challenge_id': str(ch_id),
                'display_duration_sec': '25',
                'file': (io.BytesIO(TINY_PNG), 'clue_board.png')
            }, content_type='multipart/form-data')
            data = res.get_json()
            self.assertTrue(data['success'], f"upload failed: {data}")
            self.assertEqual(data['media']['media_type'], 'IMAGE')
            self.assertEqual(data['media']['display_duration_sec'], 25)
            media_id = data['media']['id']
            self.assertTrue(data['media']['file_path'].startswith(f'static/uploads/challenge_{ch_id}/'))

            # 2. Upload a video with 0 seconds => plays fully (no time cap)
            res = self.client.post('/api/upload_media', data={
                'challenge_id': str(ch_id),
                'display_duration_sec': '0',
                'file': (io.BytesIO(b'\x00\x00\x00\x18ftypmp42'), 'intro_clip.mp4')
            }, content_type='multipart/form-data')
            vid_data = res.get_json()
            self.assertTrue(vid_data['success'], f"video upload failed: {vid_data}")
            self.assertEqual(vid_data['media']['media_type'], 'VIDEO')
            self.assertEqual(vid_data['media']['display_duration_sec'], 0)

            # 3. /api/state exposes the media incl. required seconds for the projector
            state = self.client.get('/api/state').get_json()
            media = state.get('challenge_media', [])
            self.assertEqual(len(media), 2)
            durations = {m['display_duration_sec'] for m in media}
            self.assertIn(25, durations)
            self.assertIn(0, durations)

            # 4. Host media management actions
            listing = self.client.post('/api/host/control', json={
                'action': 'get_challenge_media', 'challenge_id': ch_id
            }).get_json()
            self.assertTrue(listing['success'])
            self.assertEqual(len(listing['media']), 2)

            upd = self.client.post('/api/host/control', json={
                'action': 'update_media_duration', 'media_id': media_id, 'display_duration_sec': 45
            }).get_json()
            self.assertTrue(upd['success'])
            row = query_db("SELECT display_duration_sec FROM challenge_media WHERE id = ?", (media_id,), one=True)
            self.assertEqual(row['display_duration_sec'], 45)

            # 5. Host pages render with the new media UI / live team sync hooks
            teams_html = self.client.get('/host/teams')
            self.assertEqual(teams_html.status_code, 200)
            self.assertIn(b'teamScore_', teams_html.data)
            self.assertIn(b'refreshTeamsTable', teams_html.data)

            ch_html = self.client.get('/host/challenges')
            self.assertEqual(ch_html.status_code, 200)
            self.assertIn(b'openMediaModal', ch_html.data)

            proj_html = self.client.get('/projector/challenge')
            self.assertEqual(proj_html.status_code, 200)
            self.assertIn(b'proj-media-slideshow', proj_html.data)

            # 6. Deleting the challenge removes media rows and files
            deleted = self.client.post('/api/host/control', json={
                'action': 'delete_challenge', 'challenge_id': ch_id
            }).get_json()
            self.assertTrue(deleted['success'])
            remaining = query_db("SELECT * FROM challenge_media WHERE challenge_id = ?", (ch_id,))
            self.assertEqual(len(remaining), 0)
            self.assertFalse(os.path.exists(os.path.join('static', 'uploads', f'challenge_{ch_id}')))
        finally:
            self._restore_event_state(saved_event)


if __name__ == '__main__':
    unittest.main()
