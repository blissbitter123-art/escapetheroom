from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from database import query_db
from game.round_manager import RoundManager
from game.timer_manager import TimerManager
from game.scoring import ScoringEngine

team_bp = Blueprint('team', __name__, url_prefix='/team')

def get_logged_in_team():
    team_id = session.get('team_id')
    if not team_id:
        return None
    return query_db("SELECT * FROM teams WHERE id = ?", (team_id,), one=True)

@team_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        pin = request.form.get('pin', '').strip()
        team = query_db("SELECT * FROM teams WHERE pin = ?", (pin,), one=True)
        if team:
            session['team_id'] = team['id']
            session['team_number'] = team['team_number']
            return redirect(url_for('team.home'))
        else:
            error = "Invalid Team PIN. Check credentials."
    return render_template('team/login.html', error=error)

@team_bp.route('/logout')
def logout():
    session.pop('team_id', None)
    session.pop('team_number', None)
    return redirect(url_for('team.login'))

@team_bp.route('/')
@team_bp.route('/home')
def home():
    team = get_logged_in_team()
    if not team:
        return redirect(url_for('team.login'))

    state = RoundManager.get_current_state()
    state['team_wager'] = None

    ch_id = state.get('current_challenge_id')
    submission = None
    if ch_id:
        submission = query_db("SELECT * FROM submissions WHERE team_id = ? AND challenge_id = ?",
                              (team['id'], ch_id), one=True)

        wager = query_db("SELECT * FROM wagers WHERE team_id = ? AND challenge_id = ?",
                         (team['id'], ch_id), one=True)
        state['team_wager'] = dict(wager) if wager else None

        # Clues for active challenge
        all_clues = query_db("SELECT id, challenge_id, cost_points, order_index FROM challenge_clues WHERE challenge_id = ? ORDER BY order_index ASC", (ch_id,))
        purchased = query_db("""
            SELECT cp.id, cc.id as clue_id, cc.clue_text, cp.points_spent, cp.purchased_at
            FROM clue_purchases cp
            JOIN challenge_clues cc ON cp.clue_id = cc.id
            WHERE cp.team_id = ? AND cp.challenge_id = ?
            ORDER BY cc.order_index ASC
        """, (team['id'], ch_id))
        purchased_ids = {p['clue_id'] for p in purchased}
        state['purchased_clues'] = [dict(p) for p in purchased]
        state['purchased_hints'] = [p['clue_text'] for p in purchased]
        state['challenge_clues'] = [
            {
                "id": c['id'],
                "challenge_id": c['challenge_id'],
                "cost_points": c['cost_points'],
                "order_index": c['order_index'],
                "is_purchased": c['id'] in purchased_ids
            }
            for c in all_clues
        ]
    else:
        state['purchased_clues'] = []
        state['purchased_hints'] = []
        state['challenge_clues'] = []

    return render_template('team/home.html', team=team, state=state, submission=submission)

@team_bp.route('/wager', methods=['POST'])
def lock_wager():
    """Round 3 Gamble — Step 1: lock a team's wager (SAFE / RISK / ALL_IN).

    No answer is submitted and no points change here; the gamble question
    is revealed once the wager is locked.
    """
    team = get_logged_in_team()
    if not team:
        return jsonify({"success": False, "error": "Not authenticated"}), 401

    if team['status'] == 'ELIMINATED':
        return jsonify({"success": False, "error": "Team is eliminated"}), 403

    data = request.get_json() or request.form
    challenge_id = data.get('challenge_id')
    wager_type = data.get('wager_type', '').strip()

    if not challenge_id:
        return jsonify({"success": False, "error": "Missing challenge ID"}), 400
    if not wager_type:
        return jsonify({"success": False, "error": "Missing wager type"}), 400

    try:
        challenge_id = int(challenge_id)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid challenge ID"}), 400

    success, msg = ScoringEngine.lock_wager(team['id'], challenge_id, wager_type)
    if not success:
        return jsonify({"success": False, "error": msg}), 400

    return jsonify({"success": True, "message": msg, "wager_type": wager_type.upper()})

@team_bp.route('/buy_hint', methods=['POST'])
@team_bp.route('/buy_clue', methods=['POST'])
def buy_hint():
    team = get_logged_in_team()
    if not team:
        return jsonify({"success": False, "error": "Not authenticated"}), 401

    data = request.get_json(silent=True) or request.form or {}
    clue_id = data.get('clue_id')
    challenge_id = data.get('challenge_id')

    if clue_id is not None:
        try:
            clue_id = int(clue_id)
        except (TypeError, ValueError):
            clue_id = None

    if challenge_id is not None:
        try:
            challenge_id = int(challenge_id)
        except (TypeError, ValueError):
            challenge_id = None

    from routes.api_routes import process_hint_purchase
    resp_data, status_code = process_hint_purchase(team['id'], clue_id=clue_id, challenge_id=challenge_id)
    return jsonify(resp_data), status_code

@team_bp.route('/submit', methods=['POST'])
@team_bp.route('/submit-answer', methods=['POST'])
def submit():
    team = get_logged_in_team()
    if not team:
        return jsonify({"success": False, "error": "Not authenticated"}), 401

    if team['status'] == 'ELIMINATED':
        return jsonify({"success": False, "error": "Team is eliminated"}), 403

    data = request.get_json() or request.form
    challenge_id = data.get('challenge_id')
    answer_text = (data.get('answer_text') or '').strip()
    response_time_ms = int(data.get('response_time_ms', 0))

    if not challenge_id:
        return jsonify({"success": False, "error": "Missing challenge ID"}), 400

    try:
        challenge_id = int(challenge_id)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid challenge ID"}), 400

    challenge = query_db("SELECT * FROM challenges WHERE id = ?", (challenge_id,), one=True)
    if not challenge:
        return jsonify({"success": False, "error": "Challenge not found"}), 400

    # GAMBLE WAGER Step 1: locking a wager keyword is NOT an answer submission.
    wager_keywords = {'SAFE', 'RISK', 'ALL_IN'}
    if challenge['challenge_type'] == 'GAMBLE_WAGER' and answer_text.upper() in wager_keywords:
        existing_wager = query_db("SELECT * FROM wagers WHERE team_id = ? AND challenge_id = ?",
                                  (team['id'], challenge_id), one=True)
        existing_sub = query_db("SELECT * FROM submissions WHERE team_id = ? AND challenge_id = ?",
                                (team['id'], challenge_id), one=True)
        if not existing_wager and not existing_sub:
            success, wmsg = ScoringEngine.lock_wager(team['id'], challenge_id, answer_text)
            if not success:
                return jsonify({"success": False, "error": wmsg}), 400
            return jsonify({
                "success": True,
                "wager_locked": True,
                "message": wmsg,
                "is_correct": False,
                "points_awarded": 0
            })

    # Step 2 (or standard challenges): evaluate answer via ScoringEngine
    is_corr, pts, msg = ScoringEngine.evaluate_submission(team['id'], challenge_id, answer_text, response_time_ms)

    return jsonify({
        "success": True,
        "is_correct": is_corr,
        "points_awarded": pts,
        "message": msg
    })
