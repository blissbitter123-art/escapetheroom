from game.game_engine import GameEngine
from game.round_manager import RoundManager
from database import query_db

class Final60Controller:
    ROUND_NUMBER = 4

    @classmethod
    def start(cls):
        """Start the Final 60 climax phase."""
        return GameEngine.start_final_60()

    @classmethod
    def process_final_submission(cls, team_id, code_text, response_time_ms):
        """Process final submission for a finalist team."""
        final_ch = query_db("SELECT * FROM challenges WHERE challenge_type = 'FINAL_60'", one=True)
        if not final_ch:
            return False, 0, "Final challenge not found"

        is_corr, pts, msg = GameEngine.submit_answer(team_id, final_ch['id'], code_text, response_time_ms)
        if is_corr:
            # First team to solve correctly wins!
            GameEngine.declare_winner(team_id)
            msg = "ESCAPE COMPLETE! VICTORY UNLOCKED!"
        return is_corr, pts, msg
