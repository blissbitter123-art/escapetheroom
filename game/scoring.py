import re
import json
import logging
from database import query_db, execute_db, insert_db

logger = logging.getLogger('scoring')

class ScoringEngine:
    @staticmethod
    def normalize_answer(text):
        """Normalize answer string for accurate comparison."""
        if text is None:
            return ""
        text = str(text).strip()
        # Remove extra whitespace and convert to uppercase
        text = re.sub(r'\s+', ' ', text).upper()
        return text

    @classmethod
    def evaluate_submission(cls, team_id, challenge_id, submitted_answer, response_time_ms=0):
        """Evaluate team submission and return (is_correct, points_awarded, message)."""
        team = query_db("SELECT * FROM teams WHERE id = ?", (team_id,), one=True)
        challenge = query_db("SELECT * FROM challenges WHERE id = ?", (challenge_id,), one=True)

        if not team or not challenge:
            return False, 0, "Invalid team or challenge"

        if team['status'] == 'ELIMINATED':
            return False, 0, "Team is eliminated"

        # Check existing submission
        existing = query_db("SELECT * FROM submissions WHERE team_id = ? AND challenge_id = ?",
                            (team_id, challenge_id), one=True)

        expected_action = challenge['expected_action']
        correct_answer = challenge['correct_answer']
        base_points = challenge['base_points']
        speed_bonus = challenge['speed_bonus_points']
        penalty = challenge['penalty_points']
        duration_sec = challenge['duration_sec'] or 60

        is_correct = False
        points_awarded = 0

        # TRAP: No submission expected
        if expected_action == 'NO_SUBMISSION':
            # Team actually submitted when they were told NOT to submit
            is_correct = False
            points_awarded = -penalty if penalty > 0 else -10
            msg = f"Trap triggered! -{abs(points_awarded)} pts penalty."
        
        # DOUBLE AGENT (R2 C5)
        elif challenge['challenge_type'] == 'DOUBLE_AGENT':
            norm_sub = cls.normalize_answer(submitted_answer)
            norm_corr = cls.normalize_answer(correct_answer)
            is_correct = (norm_sub == norm_corr)

            if norm_sub == 'MISUNDERSTOOD CLUE':
                points_awarded = 10
                msg = "Safe strategic option selected (+10 pts)."
            elif is_correct:
                points_awarded = 20
                msg = "Correct strategic risk! (+20 pts)."
            else:
                points_awarded = -10
                msg = "Wrong strategic risk choice (-10 pts)."

        # GAMBLE WAGER (R3 C2)
        elif challenge['challenge_type'] == 'GAMBLE_WAGER':
            norm_wager = cls.normalize_answer(submitted_answer)
            execute_db("DELETE FROM wagers WHERE team_id = ? AND challenge_id = ?", (team_id, challenge_id))
            
            if norm_wager == 'ALL_IN':
                insert_db("INSERT INTO wagers (team_id, challenge_id, wager_type, multiplier, penalty) VALUES (?, ?, 'ALL_IN', 3.0, 25)",
                          (team_id, challenge_id))
                is_correct = True
                points_awarded = 0 # Wager modifier applies to Stage A / Final score
                msg = "ALL-IN Wager locked (3x multiplier / -25 penalty)."
            elif norm_wager == 'RISK':
                insert_db("INSERT INTO wagers (team_id, challenge_id, wager_type, multiplier, penalty) VALUES (?, ?, 'RISK', 2.0, 10)",
                          (team_id, challenge_id))
                is_correct = True
                points_awarded = 0
                msg = "RISK Wager locked (2x multiplier / -10 penalty)."
            else: # SAFE
                insert_db("INSERT INTO wagers (team_id, challenge_id, wager_type, multiplier, penalty) VALUES (?, ?, 'SAFE', 1.0, 0)",
                          (team_id, challenge_id))
                is_correct = True
                points_awarded = 0
                msg = "SAFE Wager locked (1x normal multiplier)."

        # STANDARD / NUMBER / TEXT / FINAL 60
        else:
            norm_sub = cls.normalize_answer(submitted_answer)
            norm_corr = cls.normalize_answer(correct_answer)

            is_correct = (norm_sub == norm_corr)

            # Check wager multiplier if applicable
            wager = query_db("SELECT * FROM wagers WHERE team_id = ?", (team_id,), one=True)
            mult = wager['multiplier'] if wager else 1.0
            w_penalty = wager['penalty'] if wager else 0

            if is_correct:
                points_awarded = int(base_points * mult)
                # Speed bonus if within first 25% of duration
                if speed_bonus > 0 and response_time_ms > 0 and (response_time_ms <= (duration_sec * 250)):
                    points_awarded += speed_bonus
                    msg = f"Correct! +{points_awarded} pts (includes speed bonus)."
                else:
                    msg = f"Correct! +{points_awarded} pts."
            else:
                if w_penalty > 0:
                    points_awarded = -w_penalty
                    msg = f"Incorrect. Wager penalty applied (-{w_penalty} pts)."
                elif penalty > 0:
                    points_awarded = -penalty
                    msg = f"Incorrect. -{penalty} pts penalty."
                else:
                    points_awarded = 0
                    msg = "Incorrect. 0 pts awarded."

        # Insert or update submission record
        if existing:
            execute_db("""
                UPDATE submissions 
                SET answer_text = ?, is_correct = ?, points_awarded = ?, response_time_ms = ?, submitted_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (submitted_answer, 1 if is_correct else 0, points_awarded, response_time_ms, existing['id']))
            sub_id = existing['id']
        else:
            sub_id = insert_db("""
                INSERT INTO submissions (team_id, challenge_id, answer_text, is_correct, points_awarded, response_time_ms)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (team_id, challenge_id, submitted_answer, 1 if is_correct else 0, points_awarded, response_time_ms))

        # Update score history and team total score directly
        execute_db("""
            INSERT INTO scores (team_id, round_id, challenge_id, points_delta, reason)
            VALUES (?, ?, ?, ?, ?)
        """, (team_id, challenge['round_id'], challenge_id, points_awarded, f"Challenge {challenge['title']}: {msg}"))

        execute_db("UPDATE teams SET score = score + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (points_awarded, team_id))

        return is_correct, points_awarded, msg

    @classmethod
    def get_challenge_result_stats(cls, challenge_id):
        """Get submission breakdown stats for answer reveal screen."""
        ch = query_db("SELECT * FROM challenges WHERE id = ?", (challenge_id,), one=True)
        if not ch:
            return {}

        total_sub = query_db("SELECT COUNT(*) as cnt FROM submissions WHERE challenge_id = ?", (challenge_id,), one=True)['cnt']
        correct_sub = query_db("SELECT COUNT(*) as cnt FROM submissions WHERE challenge_id = ? AND is_correct = 1", (challenge_id,), one=True)['cnt']
        wrong_sub = query_db("SELECT COUNT(*) as cnt FROM submissions WHERE challenge_id = ? AND is_correct = 0", (challenge_id,), one=True)['cnt']
        
        fastest = query_db("""
            SELECT t.team_name, s.response_time_ms 
            FROM submissions s 
            JOIN teams t ON s.team_id = t.id 
            WHERE s.challenge_id = ? AND s.is_correct = 1 
            ORDER BY s.response_time_ms ASC LIMIT 1
        """, (challenge_id,), one=True)

        return {
            "challenge_title": ch['title'],
            "correct_answer": ch['correct_answer'],
            "expected_action": ch['expected_action'],
            "total_submissions": total_sub,
            "correct_count": correct_sub,
            "wrong_count": wrong_sub,
            "fastest_team": dict(fastest) if fastest else None
        }

    @staticmethod
    def recalculate_team_score(team_id):
        """Sum all points_delta for team and update teams.score."""
        total = query_db("SELECT SUM(points_delta) as total FROM scores WHERE team_id = ?", (team_id,), one=True)
        new_score = total['total'] if total and total['total'] is not None else 0
        execute_db("UPDATE teams SET score = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_score, team_id))
        return new_score

    @classmethod
    def apply_no_submission_trap_bonuses(cls, challenge_id):
        """Award points to teams that obeyed the NO_SUBMISSION trap instruction."""
        challenge = query_db("SELECT * FROM challenges WHERE id = ?", (challenge_id,), one=True)
        if not challenge or challenge['expected_action'] != 'NO_SUBMISSION':
            return 0

        active_teams = query_db("SELECT * FROM teams WHERE status != 'ELIMINATED'")
        rewarded_count = 0
        base_points = challenge['base_points']

        for team in active_teams:
            submitted = query_db("SELECT * FROM submissions WHERE team_id = ? AND challenge_id = ?",
                                 (team['id'], challenge_id), one=True)
            if not submitted:
                # Obeyed trap! Award bonus
                execute_db("""
                    INSERT INTO scores (team_id, round_id, challenge_id, points_delta, reason)
                    VALUES (?, ?, ?, ?, 'Obeyed Trap: No submission made (+10 pts)')
                """, (team['id'], challenge['round_id'], challenge_id, base_points))
                cls.recalculate_team_score(team['id'])
                rewarded_count += 1

        return rewarded_count

    @classmethod
    def manual_score_adjust(cls, team_id, points_delta, reason="Host Manual Adjustment"):
        """Host manual override to adjust score."""
        team = query_db("SELECT * FROM teams WHERE id = ?", (team_id,), one=True)
        if not team:
            return False
        
        event = query_db("SELECT * FROM event WHERE id = 1", one=True)
        cur_round = event['current_round'] if event else 1

        execute_db("""
            INSERT INTO scores (team_id, round_id, challenge_id, points_delta, reason)
            VALUES (?, ?, NULL, ?, ?)
        """, (team_id, cur_round, points_delta, reason))

        cls.recalculate_team_score(team_id)
        return True
