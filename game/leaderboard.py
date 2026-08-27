import logging
from database import query_db, execute_db

logger = logging.getLogger('leaderboard')

class LeaderboardEngine:
    @staticmethod
    def update_leaderboard():
        """Recalculate ranks for all active/surviving teams in a single transaction."""
        from database import get_db
        conn = get_db()
        try:
            teams = conn.execute("""
                SELECT t.id, t.score, t.team_number, t.status,
                       COALESCE(SUM(s.response_time_ms), 0) as total_time
                FROM teams t
                LEFT JOIN submissions s ON t.id = s.team_id AND s.is_correct = 1
                GROUP BY t.id
                ORDER BY t.score DESC, total_time ASC, t.team_number ASC
            """).fetchall()

            rank = 1
            for team in teams:
                conn.execute("UPDATE teams SET rank = ? WHERE id = ?", (rank, team['id']))
                rank += 1
            conn.commit()
        finally:
            conn.close()
            
        logger.info(f"Leaderboard ranks updated for {len(teams)} teams.")

    @classmethod
    def get_leaderboard(cls, filter_status=None, limit=None):
        """Retrieve current ranked leaderboard."""
        cls.update_leaderboard()
        
        query = "SELECT id, team_number, team_name, pin, status, score, rank FROM teams"
        args = []
        if filter_status:
            query += " WHERE status = ?"
            args.append(filter_status)
            
        query += " ORDER BY rank ASC"
        if limit:
            query += f" LIMIT {int(limit)}"
            
        return query_db(query, args)

    @classmethod
    def get_cutoff_preview(cls, cutoff_count):
        """Return teams above cutoff (survivors) and below cutoff (elimination candidates)."""
        cls.update_leaderboard()
        
        # Get all active (or non-eliminated) teams ordered by rank
        active_teams = query_db("""
            SELECT id, team_number, team_name, status, score, rank 
            FROM teams 
            WHERE status != 'ELIMINATED' 
            ORDER BY rank ASC
        """)

        survivors = active_teams[:cutoff_count]
        elimination_candidates = active_teams[cutoff_count:]

        return {
            "total_active": len(active_teams),
            "cutoff_count": cutoff_count,
            "survivors": [dict(t) for t in survivors],
            "eliminated": [dict(t) for t in elimination_candidates]
        }
