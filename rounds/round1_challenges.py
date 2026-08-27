from database import query_db

def get_round1_challenges():
    """Retrieve all challenges for Round 1."""
    return query_db("SELECT * FROM challenges WHERE round_id = 1 ORDER BY order_index ASC")

def get_challenge_by_key(key):
    """Retrieve a challenge by its unique key."""
    return query_db("SELECT * FROM challenges WHERE challenge_key = ?", (key,), one=True)
