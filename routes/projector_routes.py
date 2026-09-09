from flask import Blueprint, render_template, jsonify
from database import query_db
from game.round_manager import RoundManager
from game.timer_manager import TimerManager
from game.leaderboard import LeaderboardEngine

projector_bp = Blueprint('projector', __name__, url_prefix='/projector')

@projector_bp.route('/')
@projector_bp.route('/display')
def display():
    """Main Projector display screen (dynamically updates via API state sync)."""
    state = RoundManager.get_current_state()
    return render_template('projector/display.html', state=state)

@projector_bp.route('/intro')
def intro():
    return render_template('projector/intro.html')

@projector_bp.route('/challenge')
def challenge():
    state = RoundManager.get_current_state()
    media = []
    if state.get('current_challenge_id'):
        rows = query_db(
            "SELECT id, media_type, file_path, filename, display_duration_sec, order_index FROM challenge_media WHERE challenge_id = ? ORDER BY order_index ASC",
            (state['current_challenge_id'],)
        )
        media = [dict(m) for m in rows]
    return render_template('projector/challenge.html', state=state, media=media)

@projector_bp.route('/elimination')
def elimination():
    event = query_db("SELECT * FROM event WHERE id = 1", one=True)
    cur_round = event['current_round'] if event else 1
    cutoffs = {1: 40, 2: 20, 3: 5, 4: 1}
    target_cutoff = cutoffs.get(cur_round, 40)
    preview = LeaderboardEngine.get_cutoff_preview(target_cutoff)
    return render_template('projector/elimination.html', preview=preview, current_round=cur_round)

@projector_bp.route('/winner')
def winner():
    winner_team = query_db("SELECT * FROM teams WHERE status = 'WINNER'", one=True)
    return render_template('projector/winner.html', winner=winner_team)
