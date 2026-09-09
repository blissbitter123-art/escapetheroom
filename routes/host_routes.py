from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from config import HOST_PASSWORD, LOCAL_IP, PORT
from database import query_db
from game.round_manager import RoundManager
from game.timer_manager import TimerManager
from game.leaderboard import LeaderboardEngine
from game.game_engine import GameEngine

host_bp = Blueprint('host', __name__, url_prefix='/host')

def check_host_auth():
    return session.get('is_host', False)

@host_bp.before_request
def require_host_login():
    if request.endpoint and 'login' not in request.endpoint and not check_host_auth():
        return redirect(url_for('host.login'))

@host_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        password = request.form.get('password')
        if password == HOST_PASSWORD:
            session['is_host'] = True
            return redirect(url_for('host.dashboard'))
        else:
            error = "Invalid Host Password"
    return render_template('host/login.html', error=error)

@host_bp.route('/logout')
def logout():
    session.pop('is_host', None)
    return redirect(url_for('host.login'))

@host_bp.route('/')
@host_bp.route('/dashboard')
def dashboard():
    state = RoundManager.get_current_state()
    remaining, is_running, is_paused = TimerManager.get_remaining_sec()
    state['timer'] = {
        "remaining": remaining,
        "is_running": is_running,
        "is_paused": is_paused
    }
    challenges = query_db("SELECT * FROM challenges ORDER BY round_id ASC, order_index ASC")
    rounds = query_db("SELECT * FROM rounds ORDER BY round_number ASC")
    return render_template('host/dashboard.html', state=state, challenges=challenges, rounds=rounds, local_ip=LOCAL_IP, port=PORT)

@host_bp.route('/teams')
def teams():
    all_teams = query_db("SELECT * FROM teams ORDER BY team_number ASC")
    return render_template('host/teams.html', teams=all_teams)

@host_bp.route('/challenges')
def challenges():
    all_challenges = query_db("SELECT c.*, r.title as round_title FROM challenges c JOIN rounds r ON c.round_id = r.id ORDER BY c.round_id ASC, c.order_index ASC")
    # Attach uploaded media counts for the directory table
    media_counts = {m['challenge_id']: m['cnt'] for m in query_db("SELECT challenge_id, COUNT(*) as cnt FROM challenge_media GROUP BY challenge_id")}
    challenges_with_media = []
    for c in all_challenges:
        d = dict(c)
        d['media_count'] = media_counts.get(c['id'], 0)
        challenges_with_media.append(d)
    return render_template('host/challenges.html', challenges=challenges_with_media)

@host_bp.route('/leaderboard')
def leaderboard():
    lb = LeaderboardEngine.get_leaderboard()
    event = query_db("SELECT * FROM event WHERE id = 1", one=True)
    cur_round = event['current_round'] if event else 1
    
    # Determine target cutoff for current round
    cutoffs = {1: 40, 2: 20, 3: 5, 4: 1}
    target_cutoff = cutoffs.get(cur_round, 40)
    cutoff_preview = LeaderboardEngine.get_cutoff_preview(target_cutoff)
    
    return render_template('host/leaderboard.html', leaderboard=lb, current_round=cur_round, preview=cutoff_preview)

@host_bp.route('/settings')
def settings():
    event = query_db("SELECT * FROM event WHERE id = 1", one=True)
    return render_template('host/settings.html', event=event)
