from database import query_db

def get_round2_challenges():
    """Retrieve all challenges for Round 2."""
    return query_db("SELECT * FROM challenges WHERE round_id = 2 ORDER BY order_index ASC")
