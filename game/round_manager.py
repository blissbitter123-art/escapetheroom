import json
import logging
import os
from config import EVENT_CONFIG_PATH, TEAMS_DATA_PATH, CHALLENGES_DATA_PATH
from database import query_db, execute_db, insert_db

logger = logging.getLogger('round_manager')

class RoundManager:
    @classmethod
    def seed_initial_data(cls):
        """Seed initial rounds, teams, and challenges from JSON if empty."""
        # 1. Seed event table
        event = query_db("SELECT * FROM event WHERE id = 1", one=True)
        if not event:
            execute_db("""
                INSERT INTO event (id, event_name, status, current_round, current_phase)
                VALUES (1, 'ESCAPE THE ROOM: THE FINAL 60', 'IDLE', 1, 'INTRO')
            """)

        # 2. Seed rounds
        if not query_db("SELECT * FROM rounds"):
            with open(EVENT_CONFIG_PATH, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            for r in cfg['round_progression']:
                execute_db("""
                    INSERT INTO rounds (id, round_number, title, subtitle, status, start_team_count, end_team_count, target_duration_min)
                    VALUES (?, ?, ?, ?, 'PENDING', ?, ?, ?)
                """, (r['round_number'], r['round_number'], r['title'], r['subtitle'], r['start_teams'], r['cutoff_teams'], r['target_duration_min']))

        # 3. Seed teams
        if not query_db("SELECT * FROM teams"):
            import random
            for i in range(1, 51):
                pin = str(random.randint(1000, 9999))
                team_name = f"Team {i:02d}"
                execute_db("""
                    INSERT INTO teams (team_number, team_name, pin, status, score, rank)
                    VALUES (?, ?, ?, 'ACTIVE', 0, ?)
                """, (i, team_name, pin, i))

        # 4. Seed challenges
        if not query_db("SELECT * FROM challenges"):
            with open(CHALLENGES_DATA_PATH, 'r', encoding='utf-8') as f:
                challenges = json.load(f)
            for c in challenges:
                r_row = query_db("SELECT id FROM rounds WHERE round_number = ?", (c['round_id'],), one=True)
                actual_round_id = r_row['id'] if r_row else c['round_id']
                execute_db("""
                    INSERT INTO challenges (
                        id, round_id, mission_id, challenge_key, title, description, challenge_type,
                        duration_sec, correct_answer, expected_action, base_points, speed_bonus_points,
                        penalty_points, difficulty, display_data_json, options_json, order_index
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    c['id'], actual_round_id, c.get('mission_id', 1), c['challenge_key'], c['title'],
                    c.get('description', ''), c['challenge_type'], c.get('duration_sec', 60),
                    c.get('correct_answer', ''), c.get('expected_action', 'SUBMIT_ANSWER'),
                    c.get('base_points', 10), c.get('speed_bonus_points', 0), c.get('penalty_points', 0),
                    c.get('difficulty', 'EASY'), c.get('display_data_json', '{}'),
                    c.get('options_json', '[]'), c.get('order_index', 1)
                ))

        logger.info("Data seeding checked and completed.")

    @staticmethod
    def get_current_state():
        """Retrieve complete event state snapshot."""
        event = query_db("SELECT * FROM event WHERE id = 1", one=True)
        if not event:
            return {}

        cur_round_id = event['current_round']
        cur_challenge_id = event['current_challenge_id']

        cur_round = query_db("SELECT * FROM rounds WHERE round_number = ?", (cur_round_id,), one=True)
        cur_challenge = query_db("SELECT * FROM challenges WHERE id = ?", (cur_challenge_id,), one=True) if cur_challenge_id else None

        active_count = query_db("SELECT COUNT(*) as cnt FROM teams WHERE status IN ('ACTIVE', 'FINALIST')", one=True)['cnt']
        eliminated_count = query_db("SELECT COUNT(*) as cnt FROM teams WHERE status = 'ELIMINATED'", one=True)['cnt']

        return {
            "event_name": event['event_name'],
            "status": event['status'],
            "current_round": cur_round_id,
            "round_title": cur_round['title'] if cur_round else '',
            "current_phase": event['current_phase'],
            "current_challenge_id": cur_challenge_id,
            "active_challenge": dict(cur_challenge) if cur_challenge else None,
            "active_teams_count": active_count,
            "eliminated_teams_count": eliminated_count
        }

    @staticmethod
    def set_phase(phase_name):
        """Update current event phase (e.g. INTRO, CHALLENGE, COUNTDOWN, LEADERBOARD, ELIMINATION)."""
        execute_db("UPDATE event SET current_phase = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1", (phase_name,))

    @staticmethod
    def advance_round(target_round_number):
        """Advance to target round number."""
        execute_db("""
            UPDATE event 
            SET current_round = ?, current_challenge_id = NULL, current_phase = 'ROUND_INTRO', status = 'ROUND_ACTIVE', updated_at = CURRENT_TIMESTAMP 
            WHERE id = 1
        """, (target_round_number,))
        
        execute_db("UPDATE rounds SET status = 'IN_PROGRESS' WHERE round_number = ?", (target_round_number,))
        execute_db("UPDATE rounds SET status = 'COMPLETED' WHERE round_number < ?", (target_round_number,))
        
        insert_db("INSERT INTO event_logs (event_type, description) VALUES ('ROUND_STARTED', ?)",
                  (f"Advanced to Round {target_round_number}",))

    @staticmethod
    def set_active_challenge(challenge_id):
        """Set current active challenge by ID."""
        ch = query_db("SELECT * FROM challenges WHERE id = ?", (challenge_id,), one=True)
        if not ch:
            return False

        execute_db("""
            UPDATE event 
            SET current_challenge_id = ?, current_round = ?, current_phase = 'CHALLENGE', status = 'ROUND_ACTIVE', updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
        """, (challenge_id, ch['round_id']))

        insert_db("INSERT INTO event_logs (event_type, description, payload_json) VALUES ('CHALLENGE_STARTED', ?, ?)",
                  (f"Started challenge {ch['title']}", json.dumps({"challenge_id": challenge_id})))
        return True
