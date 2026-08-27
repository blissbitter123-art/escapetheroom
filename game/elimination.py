import logging
from database import query_db, execute_db, insert_db
from game.leaderboard import LeaderboardEngine

logger = logging.getLogger('elimination')

class EliminationEngine:
    @classmethod
    def execute_round_elimination(cls, round_number, cutoff_count):
        """Perform automated cutoff elimination for the specified round."""
        preview = LeaderboardEngine.get_cutoff_preview(cutoff_count)
        eliminated_list = preview['eliminated']
        survivors_list = preview['survivors']

        logger.info(f"Round {round_number} elimination: {len(survivors_list)} survive, {len(eliminated_list)} eliminated.")

        # Update status for eliminated teams
        for team in eliminated_list:
            cls._eliminate_single_team(team['id'], round_number, team['rank'], f"Cutoff Round {round_number}")

        # If transitioning from R3 to Final, update status of top 5 to 'FINALIST'
        if round_number == 3:
            for team in survivors_list:
                execute_db("UPDATE teams SET status = 'FINALIST' WHERE id = ?", (team['id'],))

        return {
            "survived_count": len(survivors_list),
            "eliminated_count": len(eliminated_list),
            "eliminated_teams": eliminated_list
        }

    @classmethod
    def _eliminate_single_team(cls, team_id, round_number, rank, reason):
        """Internal helper to set status ELIMINATED and record log."""
        execute_db("UPDATE teams SET status = 'ELIMINATED', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (team_id,))
        insert_db("""
            INSERT INTO eliminations (team_id, round_id, rank_at_elimination, reason)
            VALUES (?, ?, ?, ?)
        """, (team_id, round_number, rank, reason))

        # Log event
        insert_db("""
            INSERT INTO event_logs (event_type, description, team_id)
            VALUES ('TEAM_ELIMINATED', ?, ?)
        """, (f"Team ID {team_id} eliminated in Round {round_number} (Rank {rank}): {reason}", team_id))

    @classmethod
    def manual_eliminate_team(cls, team_id, reason="Host Manual Elimination"):
        """Host override to manually eliminate a team."""
        team = query_db("SELECT * FROM teams WHERE id = ?", (team_id,), one=True)
        if not team:
            return False
        
        event = query_db("SELECT * FROM event WHERE id = 1", one=True)
        cur_round = event['current_round'] if event else 1

        cls._eliminate_single_team(team_id, cur_round, team['rank'], reason)
        return True

    @classmethod
    def manual_restore_team(cls, team_id, reason="Host Manual Restoration"):
        """Host override to restore an eliminated team."""
        team = query_db("SELECT * FROM teams WHERE id = ?", (team_id,), one=True)
        if not team:
            return False

        execute_db("UPDATE teams SET status = 'ACTIVE', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (team_id,))
        execute_db("UPDATE eliminations SET restored_at = CURRENT_TIMESTAMP WHERE team_id = ? AND restored_at IS NULL", (team_id,))

        # Log event
        insert_db("""
            INSERT INTO event_logs (event_type, description, team_id)
            VALUES ('TEAM_RESTORED', ?, ?)
        """, (f"Team ID {team_id} restored by Host: {reason}", team_id))

        return True
