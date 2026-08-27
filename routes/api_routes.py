import json
from flask import Blueprint, jsonify, request, session
from database import query_db, insert_db, execute_db
from game.round_manager import RoundManager
from game.timer_manager import TimerManager
from game.leaderboard import LeaderboardEngine
from game.elimination import EliminationEngine
from game.scoring import ScoringEngine
from game.game_engine import GameEngine
from config import LOCAL_IP, PORT

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/state')
def get_state():
    """Client synchronization endpoint called by Host, Projector, and Team JS timers."""
    state = RoundManager.get_current_state()
    remaining, is_running, is_paused = TimerManager.get_remaining_sec()
    
    state['timer'] = {
        "remaining": remaining,
        "is_running": is_running,
        "is_paused": is_paused
    }
    state['local_ip'] = LOCAL_IP
    state['port'] = PORT

    ch_id = state.get('current_challenge_id')
    if ch_id:
        state['result_stats'] = ScoringEngine.get_challenge_result_stats(ch_id)

    # Include team context if logged in
    team_id = session.get('team_id')
    if team_id:
        team = query_db("SELECT id, team_number, team_name, status, score, rank FROM teams WHERE id = ?", (team_id,), one=True)
        if team:
            state['team'] = dict(team)
            # Check submission for active challenge
            ch_id = state.get('current_challenge_id')
            if ch_id:
                sub = query_db("SELECT * FROM submissions WHERE team_id = ? AND challenge_id = ?", (team_id, ch_id), one=True)
                state['team_submission'] = dict(sub) if sub else None

    return jsonify(state)

@api_bp.route('/host/control', methods=['POST'])
def host_control():
    """Host control commands router."""
    if not session.get('is_host'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    data = request.get_json() or {}
    action = data.get('action')

    if action == 'start_event':
        GameEngine.start_event()
    elif action == 'pause_event':
        GameEngine.pause_event()
    elif action == 'resume_event':
        GameEngine.resume_event()
    elif action == 'reset_event':
        full = data.get('full', False)
        GameEngine.reset_event(full_reset=full)
    elif action == 'advance_round':
        target_r = int(data.get('round_number', 1))
        RoundManager.advance_round(target_r)
    elif action == 'start_challenge':
        ch_id = int(data.get('challenge_id'))
        GameEngine.start_challenge(ch_id)
    elif action == 'end_challenge':
        GameEngine.end_challenge()
    elif action == 'set_phase':
        phase = data.get('phase', 'INTRO')
        RoundManager.set_phase(phase)
    elif action == 'extend_timer':
        sec = int(data.get('seconds', 10))
        TimerManager.extend_timer(sec)
    elif action == 'eliminate_round':
        cur_r = int(data.get('round_number', 1))
        cutoff = int(data.get('cutoff_count', 40))
        res = EliminationEngine.execute_round_elimination(cur_r, cutoff)
        RoundManager.set_phase('ELIMINATED')
        return jsonify({"success": True, "result": res})
    elif action == 'restore_team':
        team_id = int(data.get('team_id'))
        EliminationEngine.manual_restore_team(team_id)
    elif action == 'eliminate_team':
        team_id = int(data.get('team_id'))
        EliminationEngine.manual_eliminate_team(team_id)
    elif action == 'adjust_score':
        team_id = int(data.get('team_id'))
        delta = int(data.get('points_delta', 0))
        ScoringEngine.manual_score_adjust(team_id, delta)
    elif action == 'start_final_60':
        GameEngine.start_final_60()
    elif action == 'declare_winner':
        team_id = int(data.get('team_id'))
        GameEngine.declare_winner(team_id)
    elif action == 'generate_teams':
        count = int(data.get('count', 50))
        GameEngine.generate_teams(count)
    elif action == 'update_team_name':
        team_id = int(data.get('team_id'))
        new_name = data.get('team_name', '').strip()
        if new_name:
            GameEngine.update_team_name(team_id, new_name)
    elif action == 'demo_mode':
        winner = GameEngine.run_demo_simulation()
        return jsonify({"success": True, "winner": dict(winner) if winner else None})
    elif action == 'save_challenge':
        ch = data.get('challenge', {})
        ch_id = ch.get('id')
        round_id = int(ch.get('round_id', 1))
        mission_id = int(ch.get('mission_id', 1))
        challenge_key = ch.get('challenge_key', '').strip()
        title = ch.get('title', '').strip()
        description = ch.get('description', '').strip()
        challenge_type = ch.get('challenge_type', 'SPEED_TEST').strip()
        duration_sec = int(ch.get('duration_sec', 60))
        correct_answer = ch.get('correct_answer', '').strip()
        expected_action = ch.get('expected_action', 'SUBMIT_ANSWER').strip()
        base_points = int(ch.get('base_points', 10))
        speed_bonus_points = int(ch.get('speed_bonus_points', 0))
        penalty_points = int(ch.get('penalty_points', 0))
        difficulty = ch.get('difficulty', 'EASY').strip()
        display_data_json = ch.get('display_data_json', '')
        options_json = ch.get('options_json', '')
        order_index = int(ch.get('order_index', 1))

        if display_data_json and display_data_json.strip():
            try:
                json.loads(display_data_json)
            except Exception as e:
                return jsonify({"success": False, "error": f"Invalid display_data_json: {str(e)}"}), 400
        else:
            display_data_json = None

        if options_json and options_json.strip():
            try:
                json.loads(options_json)
            except Exception as e:
                return jsonify({"success": False, "error": f"Invalid options_json: {str(e)}"}), 400
        else:
            options_json = None

        if not challenge_key or not title:
            return jsonify({"success": False, "error": "Challenge Key and Title are required"}), 400

        if ch_id:
            execute_db("""
                UPDATE challenges SET
                    round_id = ?, mission_id = ?, challenge_key = ?, title = ?, description = ?,
                    challenge_type = ?, duration_sec = ?, correct_answer = ?, expected_action = ?,
                    base_points = ?, speed_bonus_points = ?, penalty_points = ?, difficulty = ?,
                    display_data_json = ?, options_json = ?, order_index = ?
                WHERE id = ?
            """, (round_id, mission_id, challenge_key, title, description, challenge_type,
                  duration_sec, correct_answer, expected_action, base_points, speed_bonus_points,
                  penalty_points, difficulty, display_data_json, options_json, order_index, ch_id))
        else:
            ch_id = insert_db("""
                INSERT INTO challenges (
                    round_id, mission_id, challenge_key, title, description, challenge_type,
                    duration_sec, correct_answer, expected_action, base_points, speed_bonus_points,
                    penalty_points, difficulty, display_data_json, options_json, order_index
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (round_id, mission_id, challenge_key, title, description, challenge_type,
                  duration_sec, correct_answer, expected_action, base_points, speed_bonus_points,
                  penalty_points, difficulty, display_data_json, options_json, order_index))
        return jsonify({"success": True, "challenge_id": ch_id})
    elif action == 'delete_challenge':
        ch_id = int(data.get('challenge_id'))
        execute_db("DELETE FROM challenges WHERE id = ?", (ch_id,))
        return jsonify({"success": True})
    elif action == 'get_challenge':
        ch_id = int(data.get('challenge_id'))
        ch = query_db("SELECT * FROM challenges WHERE id = ?", (ch_id,), one=True)
        if not ch:
            return jsonify({"success": False, "error": "Challenge not found"}), 404
        return jsonify({"success": True, "challenge": dict(ch)})
    else:
        return jsonify({"success": False, "error": f"Unknown action '{action}'"}), 400

    return jsonify({"success": True, "state": RoundManager.get_current_state()})

@api_bp.route('/leaderboard')
def get_leaderboard():
    lb = LeaderboardEngine.get_leaderboard()
    return jsonify([dict(row) for row in lb])

@api_bp.route('/logs')
def get_logs():
    logs = query_db("SELECT * FROM event_logs ORDER BY created_at DESC LIMIT 50")
    return jsonify([dict(l) for l in logs])
