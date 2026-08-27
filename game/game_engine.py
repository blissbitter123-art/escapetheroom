import json
import logging
import random
import time
from database import query_db, execute_db, insert_db
from game.round_manager import RoundManager
from game.timer_manager import TimerManager
from game.scoring import ScoringEngine
from game.leaderboard import LeaderboardEngine
from game.elimination import EliminationEngine

logger = logging.getLogger('game_engine')

class GameEngine:
    @classmethod
    def initialize(cls):
        """Seed DB and update leaderboard on engine startup."""
        RoundManager.seed_initial_data()
        LeaderboardEngine.update_leaderboard()

    @classmethod
    def start_event(cls):
        """Start the Escape Room event."""
        execute_db("UPDATE event SET status = 'ROUND_ACTIVE', current_phase = 'INTRO', updated_at = CURRENT_TIMESTAMP WHERE id = 1")
        insert_db("INSERT INTO event_logs (event_type, description) VALUES ('EVENT_STARTED', 'Escape The Room event officially started.')")

    @classmethod
    def pause_event(cls):
        """Pause current event and timer."""
        TimerManager.pause_timer()
        insert_db("INSERT INTO event_logs (event_type, description) VALUES ('EVENT_PAUSED', 'Event state paused by host.')")

    @classmethod
    def resume_event(cls):
        """Resume current event and timer."""
        TimerManager.resume_timer()
        insert_db("INSERT INTO event_logs (event_type, description) VALUES ('EVENT_RESUMED', 'Event state resumed by host.')")

    @classmethod
    def reset_event(cls, full_reset=False):
        """Reset event state safely without dropping tables."""
        if full_reset:
            execute_db("UPDATE event SET current_challenge_id = NULL WHERE id = 1")
            execute_db("DELETE FROM submissions")
            execute_db("DELETE FROM scores")
            execute_db("DELETE FROM wagers")
            execute_db("DELETE FROM eliminations")
            execute_db("DELETE FROM event_logs")
            execute_db("DELETE FROM challenges")
            execute_db("DELETE FROM teams")
            execute_db("DELETE FROM rounds")
            execute_db("""
                UPDATE event 
                SET status = 'IDLE', current_round = 1, current_challenge_id = NULL, current_phase = 'INTRO',
                    challenge_start_time = NULL, challenge_paused_at = NULL, pause_accumulated_sec = 0, challenge_duration_sec = 0
                WHERE id = 1
            """)
            RoundManager.seed_initial_data()
            insert_db("INSERT INTO event_logs (event_type, description) VALUES ('FULL_EVENT_RESET', 'Full event reset executed.')")
            logger.info("Full event reset completed.")
        else:
            # Reset current round state only
            event = query_db("SELECT * FROM event WHERE id = 1", one=True)
            cur_round = event['current_round'] if event else 1
            execute_db("""
                UPDATE event 
                SET current_challenge_id = NULL, current_phase = 'ROUND_INTRO',
                    challenge_start_time = NULL, challenge_paused_at = NULL, pause_accumulated_sec = 0
                WHERE id = 1
            """)
            insert_db("INSERT INTO event_logs (event_type, description) VALUES ('ROUND_RESET', ?)", (f"Round {cur_round} state reset.",))

    @classmethod
    def start_challenge(cls, challenge_id):
        """Start a specific challenge and trigger authoritative timer."""
        ch = query_db("SELECT * FROM challenges WHERE id = ?", (challenge_id,), one=True)
        if not ch:
            return False

        RoundManager.set_active_challenge(challenge_id)
        TimerManager.start_timer(ch['duration_sec'])
        return True

    @classmethod
    def end_challenge(cls):
        """End current active challenge and trigger trap check."""
        event = query_db("SELECT * FROM event WHERE id = 1", one=True)
        ch_id = event['current_challenge_id'] if event else None

        if ch_id:
            ch = query_db("SELECT * FROM challenges WHERE id = ?", (ch_id,), one=True)
            if ch and ch['expected_action'] == 'NO_SUBMISSION':
                # Apply bonus to teams that obeyed no submission rule!
                ScoringEngine.apply_no_submission_trap_bonuses(ch_id)

        RoundManager.set_phase('RESULT')
        LeaderboardEngine.update_leaderboard()
        insert_db("INSERT INTO event_logs (event_type, description) VALUES ('CHALLENGE_ENDED', 'Challenge ended by host.')")

    @classmethod
    def submit_answer(cls, team_id, challenge_id, answer_text, response_time_ms=0, update_rank=True):
        """Process team answer submission."""
        is_corr, pts, msg = ScoringEngine.evaluate_submission(team_id, challenge_id, answer_text, response_time_ms)
        if update_rank:
            LeaderboardEngine.update_leaderboard()

        insert_db("""
            INSERT INTO event_logs (event_type, description, team_id, payload_json)
            VALUES (?, ?, ?, ?)
        """, (
            'ANSWER_CORRECT' if is_corr else 'ANSWER_WRONG',
            f"Team {team_id} submitted for Challenge {challenge_id}: {msg}",
            team_id,
            json.dumps({"answer": answer_text, "points": pts, "correct": is_corr})
        ))
        return is_corr, pts, msg

    @classmethod
    def start_final_60(cls):
        """Start the Final 60 Climax stage for Top 5 finalists!"""
        # Ensure only Top 5 finalists exist in ACTIVE/FINALIST status
        finalists = query_db("SELECT * FROM teams WHERE status = 'FINALIST' ORDER BY rank ASC")
        if not finalists:
            # Pick top 5 active teams
            LeaderboardEngine.update_leaderboard()
            top5 = query_db("SELECT * FROM teams WHERE status != 'ELIMINATED' ORDER BY rank ASC LIMIT 5")
            for t in top5:
                execute_db("UPDATE teams SET status = 'FINALIST' WHERE id = ?", (t['id'],))

        # Get Final 60 challenge
        final_ch = query_db("SELECT * FROM challenges WHERE challenge_type = 'FINAL_60'", one=True)
        if final_ch:
            cls.start_challenge(final_ch['id'])
            execute_db("UPDATE event SET current_phase = 'FINAL_60', status = 'FINAL_ACTIVE' WHERE id = 1")
            insert_db("INSERT INTO event_logs (event_type, description) VALUES ('FINAL_STARTED', 'THE FINAL 60 SECONDS CLIMAX STARTED!')")
            return True
        return False

    @classmethod
    def declare_winner(cls, team_id):
        """Declare winner and complete event."""
        team = query_db("SELECT * FROM teams WHERE id = ?", (team_id,), one=True)
        if not team:
            return False

        execute_db("UPDATE teams SET status = 'WINNER' WHERE id = ?", (team_id,))
        execute_db("UPDATE event SET status = 'ENDED', current_phase = 'WINNER', updated_at = CURRENT_TIMESTAMP WHERE id = 1")

        insert_db("""
            INSERT INTO event_logs (event_type, description, team_id)
            VALUES ('WINNER_DECLARED', ?, ?)
        """, (f"TEAM {team['team_number']} ({team['team_name']}) DECLARED ULTIMATE WINNER OF ESCAPE THE ROOM!", team_id))

        return True

    @classmethod
    def generate_teams(cls, count):
        """Pre-game setup: Delete all existing teams and generate `count` new teams with random PINs."""
        execute_db("DELETE FROM submissions")
        execute_db("DELETE FROM scores")
        execute_db("DELETE FROM wagers")
        execute_db("DELETE FROM eliminations")
        execute_db("DELETE FROM teams")
        
        for i in range(1, count + 1):
            pin = str(random.randint(1000, 9999))
            team_name = f"Team {i:02d}"
            execute_db("""
                INSERT INTO teams (team_number, team_name, pin, status, score, rank)
                VALUES (?, ?, ?, 'ACTIVE', 0, ?)
            """, (i, team_name, pin, i))
            
        insert_db("INSERT INTO event_logs (event_type, description) VALUES ('TEAMS_GENERATED', ?)", (f"Generated {count} new teams with random PINs.",))
        return True

    @classmethod
    def update_team_name(cls, team_id, new_name):
        """Host action to rename a team."""
        execute_db("UPDATE teams SET team_name = ? WHERE id = ?", (new_name, team_id))
        insert_db("INSERT INTO event_logs (event_type, description) VALUES ('TEAM_RENAMED', ?)", (f"Team {team_id} renamed to {new_name}.",))
        return True

    @classmethod
    def run_demo_simulation(cls):
        """DEMO MODE: Simulate entire event (50 -> 40 -> 20 -> 5 -> Winner)."""
        from database import get_db
        cls.reset_event(full_reset=True)
        cls.start_event()

        conn = get_db()
        try:
            all_teams = conn.execute("SELECT * FROM teams").fetchall()

            # Simulate Round 1 (8 challenges)
            r1_challenges = conn.execute("SELECT c.* FROM challenges c JOIN rounds r ON c.round_id = r.id WHERE r.round_number = 1 ORDER BY c.order_index ASC").fetchall()
            for ch in r1_challenges:
                for t in all_teams:
                    if ch['expected_action'] == 'NO_SUBMISSION':
                        if random.random() < 0.2:
                            cls.submit_answer(t['id'], ch['id'], "5", 5000, update_rank=False)
                    else:
                        ans = ch['correct_answer'] if random.random() < 0.8 else "WRONG"
                        cls.submit_answer(t['id'], ch['id'], ans, random.randint(3000, 25000), update_rank=False)
                LeaderboardEngine.update_leaderboard()
            
            # Round 1 Elimination (50 -> 40)
            EliminationEngine.execute_round_elimination(1, 40)
            RoundManager.advance_round(2)

            # Simulate Round 2 (5 missions)
            survivors_r2 = conn.execute("SELECT * FROM teams WHERE status != 'ELIMINATED'").fetchall()
            r2_challenges = conn.execute("SELECT c.* FROM challenges c JOIN rounds r ON c.round_id = r.id WHERE r.round_number = 2 ORDER BY c.order_index ASC").fetchall()
            for ch in r2_challenges:
                for t in survivors_r2:
                    ans = ch['correct_answer'] if random.random() < 0.75 else "WRONG"
                    cls.submit_answer(t['id'], ch['id'], ans, random.randint(4000, 30000), update_rank=False)
                LeaderboardEngine.update_leaderboard()

            # Round 2 Elimination (40 -> 20)
            EliminationEngine.execute_round_elimination(2, 20)
            RoundManager.advance_round(3)

            # Simulate Round 3 (Lock & Gamble)
            survivors_r3 = conn.execute("SELECT * FROM teams WHERE status != 'ELIMINATED'").fetchall()
            r3_challenges = conn.execute("SELECT c.* FROM challenges c JOIN rounds r ON c.round_id = r.id WHERE r.round_number = 3 ORDER BY c.order_index ASC").fetchall()
            for ch in r3_challenges:
                for t in survivors_r3:
                    if ch['challenge_type'] == 'GAMBLE_WAGER':
                        wager = random.choice(['SAFE', 'RISK', 'ALL_IN'])
                        cls.submit_answer(t['id'], ch['id'], wager, 4000, update_rank=False)
                    else:
                        ans = ch['correct_answer'] if random.random() < 0.7 else "WRONG"
                        cls.submit_answer(t['id'], ch['id'], ans, random.randint(5000, 35000), update_rank=False)
                LeaderboardEngine.update_leaderboard()

            # Round 3 Elimination (20 -> 5)
            EliminationEngine.execute_round_elimination(3, 5)

            # Start Final 60
            cls.start_final_60()
            finalists = conn.execute("SELECT * FROM teams WHERE status = 'FINALIST' ORDER BY rank ASC").fetchall()
            final_ch = conn.execute("SELECT * FROM challenges WHERE challenge_type = 'FINAL_60'").fetchone()

            # Winning finalist submits correct answer fastest
            winner_team = finalists[0]
            cls.submit_answer(winner_team['id'], final_ch['id'], final_ch['correct_answer'], 12000)
            cls.declare_winner(winner_team['id'])
        finally:
            conn.close()

        logger.info("Demo rehearsal simulation successfully finished!")
        return winner_team
