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
    ch_id = state.get('current_challenge_id')
    submission = None
    if ch_id:
        submission = query_db("SELECT * FROM submissions WHERE team_id = ? AND challenge_id = ?",
                              (team['id'], ch_id), one=True)

    return render_template('team/home.html', team=team, state=state, submission=submission)

@team_bp.route('/submit', methods=['POST'])
def submit():
    team = get_logged_in_team()
    if not team:
        return jsonify({"success": False, "error": "Not authenticated"}), 401

    if team['status'] == 'ELIMINATED':
        return jsonify({"success": False, "error": "Team is eliminated"}), 403

    data = request.get_json() or request.form
    challenge_id = data.get('challenge_id')
    answer_text = data.get('answer_text', '').strip()
    response_time_ms = int(data.get('response_time_ms', 0))

    if not challenge_id:
        return jsonify({"success": False, "error": "Missing challenge ID"}), 400

    # Evaluate answer via ScoringEngine
    is_corr, pts, msg = ScoringEngine.evaluate_submission(team['id'], challenge_id, answer_text, response_time_ms)

    return jsonify({
        "success": True,
        "is_correct": is_corr,
        "points_awarded": pts,
        "message": msg
    })
