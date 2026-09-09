import json
import os
import uuid
from flask import Blueprint, jsonify, request, session
from database import query_db, insert_db, execute_db
from game.round_manager import RoundManager
from game.timer_manager import TimerManager
from game.leaderboard import LeaderboardEngine
from game.elimination import EliminationEngine
from game.scoring import ScoringEngine
from game.game_engine import GameEngine
from config import LOCAL_IP, PORT, UPLOADS_DIR
from werkzeug.utils import secure_filename

api_bp = Blueprint('api', __name__, url_prefix='/api')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'webm', 'mov', 'avi'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def _remove_challenge_upload_dir_if_empty(challenge_id):
    """Delete the challenge's upload folder if no media files remain."""
    ch_upload_dir = os.path.join(UPLOADS_DIR, f'challenge_{challenge_id}')
    try:
        if os.path.isdir(ch_upload_dir) and not os.listdir(ch_upload_dir):
            os.rmdir(ch_upload_dir)
    except OSError:
        pass

@api_bp.route('/state')
def get_state():
    """Client synchronization endpoint called by Host, Projector, and Team JS timers."""
    state = RoundManager.get_current_state()
    remaining, is_running, is_paused = TimerManager.get_remaining_sec()
    media_timer = TimerManager.get_media_timer()

    event = query_db("SELECT * FROM event WHERE id = 1", one=True)
    total_dur = event['challenge_duration_sec'] if event else 0
    start_time = event['challenge_start_time'] if event else None
    pause_acc = event['pause_accumulated_sec'] if event else 0

    state['timer'] = {
        "remaining": remaining,
        "is_running": is_running,
        "is_paused": is_paused,
        "total_duration": total_dur,
        "start_time": start_time,
        "pause_accumulated": pause_acc
    }
    state['media_timer'] = media_timer
    state['media_hide_at'] = media_timer['hide_at']
    state['media_visibility_duration'] = media_timer['visibility_duration']
    state['local_ip'] = LOCAL_IP
    state['port'] = PORT

    ch_id = state.get('current_challenge_id')
    if ch_id:
        state['result_stats'] = ScoringEngine.get_challenge_result_stats(ch_id)

        # Include challenge media (with required display duration in seconds)
        media = query_db("SELECT id, media_type, file_path, filename, display_duration_sec, order_index FROM challenge_media WHERE challenge_id = ? ORDER BY order_index ASC", (ch_id,))
        media_list = [dict(m) for m in media] if media else []
        state['challenge_media'] = media_list
        state['media_url'] = f"/{media_list[0]['file_path']}" if media_list else None
        if state.get('active_challenge'):
            state['active_challenge']['media_url'] = state['media_url']
            state['active_challenge']['media_visibility_duration'] = media_timer['visibility_duration']
    else:
        state['challenge_media'] = []
        state['media_url'] = None

    # Include team context if logged in
    team_id = session.get('team_id')
    if team_id:
        team = query_db("SELECT id, team_number, team_name, status, score, rank, round3_wager_type FROM teams WHERE id = ?", (team_id,), one=True)
        if team:
            state['team'] = dict(team)
            # Check submission for active challenge
            if ch_id:
                sub = query_db("SELECT * FROM submissions WHERE team_id = ? AND challenge_id = ?", (team_id, ch_id), one=True)
                state['team_submission'] = dict(sub) if sub else None

                # Locked gamble wager for this team on the active challenge (if any)
                team_wager = query_db("SELECT * FROM wagers WHERE team_id = ? AND challenge_id = ?",
                                      (team_id, ch_id), one=True)
                state['team_wager'] = dict(team_wager) if team_wager else None

                # Clues / Hints for active challenge
                all_clues = query_db("SELECT id, challenge_id, cost_points, order_index FROM challenge_clues WHERE challenge_id = ? ORDER BY order_index ASC", (ch_id,))
                purchased = query_db("""
                    SELECT cp.id, cc.id as clue_id, cc.clue_text, cp.points_spent, cp.purchased_at
                    FROM clue_purchases cp
                    JOIN challenge_clues cc ON cp.clue_id = cc.id
                    WHERE cp.team_id = ? AND cp.challenge_id = ?
                    ORDER BY cc.order_index ASC
                """, (team_id, ch_id))
                purchased_clue_ids = {p['clue_id'] for p in purchased}
                state['purchased_clues'] = [dict(p) for p in purchased]
                state['purchased_hints'] = [p['clue_text'] for p in purchased]
                state['challenge_clues'] = [
                    {
                        "id": c['id'],
                        "challenge_id": c['challenge_id'],
                        "cost_points": c['cost_points'],
                        "order_index": c['order_index'],
                        "is_purchased": c['id'] in purchased_clue_ids
                    }
                    for c in all_clues
                ]
            else:
                state['purchased_clues'] = []
                state['purchased_hints'] = []
                state['challenge_clues'] = []

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
        raw_id = data.get('challenge_id') if data.get('challenge_id') is not None else data.get('question_id')
        ch = None
        if raw_id is not None:
            try:
                ch = query_db("SELECT * FROM challenges WHERE id = ?", (int(raw_id),), one=True)
            except (ValueError, TypeError):
                pass
            if not ch:
                ch = query_db("SELECT * FROM challenges WHERE challenge_key = ?", (str(raw_id),), one=True)
            if not ch:
                norm_query = str(raw_id).lower().replace('_', '').replace('-', '')
                all_chs = query_db("SELECT * FROM challenges")
                for candidate in all_chs:
                    cand_key = candidate['challenge_key'].lower().replace('_', '').replace('-', '')
                    if cand_key.startswith(norm_query) or norm_query == cand_key:
                        ch = candidate
                        break

        if not ch:
            return jsonify({"success": False, "error": f"Challenge not found: {raw_id}"}), 404

        ch_id = ch['id']
        duration = data.get('duration') if data.get('duration') is not None else data.get('duration_sec')
        media_dur = data.get('media_visibility_duration') if data.get('media_visibility_duration') is not None else data.get('media_visibility_duration_sec')

        if ch and ch['challenge_type'] == 'GAMBLE_WAGER':
            # Fresh gamble run: clear stale wagers so teams re-pick SAFE/RISK/ALL_IN
            execute_db("DELETE FROM wagers WHERE challenge_id = ?", (ch_id,))
            execute_db("UPDATE teams SET round3_wager_type = NULL")

        GameEngine.start_challenge(
            ch_id,
            duration_sec=int(duration) if duration is not None else None,
            media_visibility_sec=int(media_dur) if media_dur is not None else None
        )
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

        media_visibility_duration_sec = int(ch.get('media_visibility_duration_sec', 15))

        if ch_id:
            execute_db("""
                UPDATE challenges SET
                    round_id = ?, mission_id = ?, challenge_key = ?, title = ?, description = ?,
                    challenge_type = ?, duration_sec = ?, correct_answer = ?, expected_action = ?,
                    base_points = ?, speed_bonus_points = ?, penalty_points = ?, difficulty = ?,
                    display_data_json = ?, options_json = ?, media_visibility_duration_sec = ?, order_index = ?
                WHERE id = ?
            """, (round_id, mission_id, challenge_key, title, description, challenge_type,
                  duration_sec, correct_answer, expected_action, base_points, speed_bonus_points,
                  penalty_points, difficulty, display_data_json, options_json, media_visibility_duration_sec, order_index, ch_id))
        else:
            ch_id = insert_db("""
                INSERT INTO challenges (
                    round_id, mission_id, challenge_key, title, description, challenge_type,
                    duration_sec, correct_answer, expected_action, base_points, speed_bonus_points,
                    penalty_points, difficulty, display_data_json, options_json, media_visibility_duration_sec, order_index
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (round_id, mission_id, challenge_key, title, description, challenge_type,
                  duration_sec, correct_answer, expected_action, base_points, speed_bonus_points,
                  penalty_points, difficulty, display_data_json, options_json, media_visibility_duration_sec, order_index))

        # Save clues if provided
        clues_data = ch.get('clues', None)
        if clues_data is not None:
            # Delete existing clues for this challenge first
            execute_db("DELETE FROM challenge_clues WHERE challenge_id = ?", (ch_id,))
            for idx, clue in enumerate(clues_data):
                clue_text = clue.get('clue_text', '').strip()
                cost_points = int(clue.get('cost_points', 5))
                if clue_text:
                    insert_db("""
                        INSERT INTO challenge_clues (challenge_id, clue_text, cost_points, order_index)
                        VALUES (?, ?, ?, ?)
                    """, (ch_id, clue_text, cost_points, idx + 1))

        return jsonify({"success": True, "challenge_id": ch_id})
    elif action == 'delete_challenge':
        ch_id = int(data.get('challenge_id'))
        # Delete associated media files from disk
        media_rows = query_db("SELECT file_path FROM challenge_media WHERE challenge_id = ?", (ch_id,))
        for m in media_rows:
            fpath = os.path.join(os.path.dirname(UPLOADS_DIR), '..', m['file_path'].lstrip('/'))
            # Construct absolute path from static root
            abs_path = os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(UPLOADS_DIR)), m['file_path'].lstrip('/')))
            if os.path.exists(abs_path):
                os.remove(abs_path)
        execute_db("DELETE FROM challenge_media WHERE challenge_id = ?", (ch_id,))
        execute_db("DELETE FROM challenge_clues WHERE challenge_id = ?", (ch_id,))
        execute_db("DELETE FROM clue_purchases WHERE challenge_id = ?", (ch_id,))
        execute_db("DELETE FROM challenges WHERE id = ?", (ch_id,))
        _remove_challenge_upload_dir_if_empty(ch_id)
        return jsonify({"success": True})
    elif action == 'get_challenge':
        ch_id = int(data.get('challenge_id'))
        ch = query_db("SELECT * FROM challenges WHERE id = ?", (ch_id,), one=True)
        if not ch:
            return jsonify({"success": False, "error": "Challenge not found"}), 404
        ch_dict = dict(ch)
        # Include clues
        clues = query_db("SELECT * FROM challenge_clues WHERE challenge_id = ? ORDER BY order_index ASC", (ch_id,))
        ch_dict['clues'] = [dict(c) for c in clues] if clues else []
        # Include media
        media = query_db("SELECT * FROM challenge_media WHERE challenge_id = ? ORDER BY order_index ASC", (ch_id,))
        ch_dict['media'] = [dict(m) for m in media] if media else []
        return jsonify({"success": True, "challenge": ch_dict})
    elif action == 'delete_challenge_media':
        media_id = int(data.get('media_id'))
        media_row = query_db("SELECT * FROM challenge_media WHERE id = ?", (media_id,), one=True)
        if media_row:
            # Remove file from disk
            base_dir = os.path.dirname(os.path.dirname(UPLOADS_DIR))
            abs_path = os.path.normpath(os.path.join(base_dir, media_row['file_path'].lstrip('/')))
            if os.path.exists(abs_path):
                os.remove(abs_path)
            execute_db("DELETE FROM challenge_media WHERE id = ?", (media_id,))
            _remove_challenge_upload_dir_if_empty(media_row['challenge_id'])
        return jsonify({"success": True})
    elif action == 'get_challenge_media':
        ch_id = int(data.get('challenge_id'))
        media = query_db("SELECT * FROM challenge_media WHERE challenge_id = ? ORDER BY order_index ASC", (ch_id,))
        return jsonify({"success": True, "media": [dict(m) for m in media] if media else []})
    elif action == 'update_media_duration':
        media_id = int(data.get('media_id'))
        try:
            duration = int(data.get('display_duration_sec', 10))
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Invalid duration value"}), 400
        duration = max(0, min(duration, 3600))
        execute_db("UPDATE challenge_media SET display_duration_sec = ? WHERE id = ?", (duration, media_id))
        return jsonify({"success": True, "media_id": media_id, "display_duration_sec": duration})
    else:
        return jsonify({"success": False, "error": f"Unknown action '{action}'"}), 400

    return jsonify({"success": True, "state": RoundManager.get_current_state()})


@api_bp.route('/upload_media', methods=['POST'])
def upload_media():
    """Handle media file upload for a challenge."""
    if not session.get('is_host'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    challenge_id = request.form.get('challenge_id')
    if not challenge_id:
        return jsonify({"success": False, "error": "Missing challenge_id"}), 400

    challenge_id = int(challenge_id)

    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": f"File type not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

    # Create challenge-specific upload directory
    ch_upload_dir = os.path.join(UPLOADS_DIR, f'challenge_{challenge_id}')
    os.makedirs(ch_upload_dir, exist_ok=True)

    # Generate unique filename
    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex[:12]}.{ext}"
    safe_name = secure_filename(unique_name)
    file_path = os.path.join(ch_upload_dir, safe_name)

    file.save(file_path)

    # Determine media type
    video_exts = {'mp4', 'webm', 'mov', 'avi'}
    media_type = 'VIDEO' if ext in video_exts else 'IMAGE'

    # Required display duration in seconds (0 = play full video, no time cap)
    try:
        display_duration_sec = int(request.form.get('display_duration_sec', 10))
    except (TypeError, ValueError):
        display_duration_sec = 10
    display_duration_sec = max(0, min(display_duration_sec, 3600))
    if display_duration_sec <= 0:
        display_duration_sec = 10 if media_type == 'IMAGE' else 0

    # Relative path for URL serving (from static/)
    rel_path = f"static/uploads/challenge_{challenge_id}/{safe_name}"

    # Get next order index
    existing_count = query_db("SELECT COUNT(*) as cnt FROM challenge_media WHERE challenge_id = ?", (challenge_id,), one=True)['cnt']

    media_id = insert_db("""
        INSERT INTO challenge_media (challenge_id, media_type, file_path, filename, display_duration_sec, order_index)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (challenge_id, media_type, rel_path, file.filename, display_duration_sec, existing_count + 1))

    return jsonify({
        "success": True,
        "media": {
            "id": media_id,
            "media_type": media_type,
            "file_path": rel_path,
            "filename": file.filename,
            "display_duration_sec": display_duration_sec,
            "order_index": existing_count + 1
        }
    })


@api_bp.route('/leaderboard')
def get_leaderboard():
    lb = LeaderboardEngine.get_leaderboard()
    return jsonify([dict(row) for row in lb])

@api_bp.route('/logs')
def get_logs():
    logs = query_db("SELECT * FROM event_logs ORDER BY created_at DESC LIMIT 50")
    return jsonify([dict(l) for l in logs])

def process_hint_purchase(team_id, clue_id=None, challenge_id=None):
    """Process hint purchase for a team."""
    team = query_db("SELECT * FROM teams WHERE id = ?", (team_id,), one=True)
    if not team:
        return {"success": False, "error": "Team not found"}, 404

    if team['status'] == 'ELIMINATED':
        return {"success": False, "error": "Team is eliminated"}, 403

    event = query_db("SELECT * FROM event WHERE id = 1", one=True)
    cur_ch_id = event['current_challenge_id'] if event else None
    ch_id = challenge_id or cur_ch_id

    if not ch_id:
        return {"success": False, "error": "No active challenge"}, 400

    # If clue_id is specified
    if clue_id:
        clue = query_db("SELECT * FROM challenge_clues WHERE id = ?", (clue_id,), one=True)
        if not clue:
            return {"success": False, "error": "Clue not found"}, 404
    else:
        # Find next unpurchased clue for this challenge
        purchased_rows = query_db("SELECT clue_id FROM clue_purchases WHERE team_id = ? AND challenge_id = ?", (team_id, ch_id))
        purchased_ids = [r['clue_id'] for r in purchased_rows] if purchased_rows else []
        if purchased_ids:
            placeholders = ','.join('?' * len(purchased_ids))
            clue = query_db(f"SELECT * FROM challenge_clues WHERE challenge_id = ? AND id NOT IN ({placeholders}) ORDER BY order_index ASC LIMIT 1", (ch_id, *purchased_ids), one=True)
        else:
            clue = query_db("SELECT * FROM challenge_clues WHERE challenge_id = ? ORDER BY order_index ASC LIMIT 1", (ch_id,), one=True)

        if not clue:
            all_purchased = query_db("""
                SELECT cc.clue_text, cp.points_spent FROM clue_purchases cp
                JOIN challenge_clues cc ON cp.clue_id = cc.id
                WHERE cp.team_id = ? AND cp.challenge_id = ?
                ORDER BY cc.order_index DESC LIMIT 1
            """, (team_id, ch_id), one=True)
            if all_purchased:
                return {
                    "success": True,
                    "hint": all_purchased['clue_text'],
                    "already_purchased": True,
                    "remaining_score": team['score'],
                    "message": "All hints already purchased for this challenge"
                }, 200
            return {"success": False, "error": "No hints available for this challenge"}, 404

    # Check if already purchased
    existing = query_db("SELECT * FROM clue_purchases WHERE team_id = ? AND clue_id = ?", (team_id, clue['id']), one=True)
    if existing:
        return {
            "success": True,
            "hint": clue['clue_text'],
            "already_purchased": True,
            "points_spent": existing['points_spent'],
            "remaining_score": team['score'],
            "message": "Hint already purchased"
        }, 200

    cost = clue['cost_points']
    if team['score'] < cost:
        return {
            "success": False,
            "error": f"Insufficient points! You have {team['score']} pts, but this hint costs {cost} pts. Score cannot go negative."
        }, 400

    ch = query_db("SELECT * FROM challenges WHERE id = ?", (clue['challenge_id'],), one=True)
    round_id = ch['round_id'] if ch else (event['current_round'] if event else 1)

    # Deduct points from team score
    execute_db("UPDATE teams SET score = score - ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (cost, team_id))

    # Record score delta
    execute_db("""
        INSERT INTO scores (team_id, round_id, challenge_id, points_delta, reason)
        VALUES (?, ?, ?, ?, ?)
    """, (team_id, round_id, clue['challenge_id'], -cost, f"Purchased Hint for {ch['title'] if ch else 'Challenge'} (-{cost} pts)"))

    # Record clue purchase
    insert_db("""
        INSERT INTO clue_purchases (team_id, clue_id, challenge_id, points_spent)
        VALUES (?, ?, ?, ?)
    """, (team_id, clue['id'], clue['challenge_id'], cost))

    # Log event
    insert_db("""
        INSERT INTO event_logs (event_type, description, team_id, payload_json)
        VALUES ('CLUE_PURCHASED', ?, ?, ?)
    """, (f"Team {team['team_number']} bought a hint for challenge {clue['challenge_id']} (-{cost} pts)", team_id, json.dumps({"clue_id": clue['id'], "cost": cost})))

    # Update leaderboard so Host and Projector show updated score on next poll
    try:
        LeaderboardEngine.update_leaderboard()
    except Exception:
        pass

    updated_team = query_db("SELECT score FROM teams WHERE id = ?", (team_id,), one=True)
    remaining_score = updated_team['score'] if updated_team else (team['score'] - cost)

    return {
        "success": True,
        "hint": clue['clue_text'],
        "clue_id": clue['id'],
        "points_spent": cost,
        "remaining_score": remaining_score,
        "message": f"Hint purchased! (-{cost} pts)"
    }, 200

@api_bp.route('/buy_hint', methods=['POST'])
@api_bp.route('/buy_clue', methods=['POST'])
def buy_hint():
    team_id = session.get('team_id')
    if not team_id:
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

    resp_data, status_code = process_hint_purchase(team_id, clue_id=clue_id, challenge_id=challenge_id)
    return jsonify(resp_data), status_code

@api_bp.route('/wager', methods=['POST'])
def api_lock_wager():
    team_id = session.get('team_id')
    if not team_id:
        return jsonify({"success": False, "error": "Not authenticated"}), 401

    data = request.get_json(silent=True) or request.form or {}
    challenge_id = data.get('challenge_id')
    wager_type = (data.get('wager_type') or '').strip()

    if not challenge_id:
        event = query_db("SELECT current_challenge_id FROM event WHERE id = 1", one=True)
        challenge_id = event['current_challenge_id'] if event else None

    if not challenge_id or not wager_type:
        return jsonify({"success": False, "error": "Missing challenge ID or wager type"}), 400

    try:
        challenge_id = int(challenge_id)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid challenge ID"}), 400

    success, msg = ScoringEngine.lock_wager(team_id, challenge_id, wager_type)
    if not success:
        return jsonify({"success": False, "error": msg}), 400

    return jsonify({"success": True, "message": msg, "wager_type": wager_type.upper()})

@api_bp.route('/submit-answer', methods=['POST'])
@api_bp.route('/submit', methods=['POST'])
def api_submit_answer():
    team_id = session.get('team_id')
    if not team_id:
        return jsonify({"success": False, "error": "Not authenticated"}), 401

    data = request.get_json(silent=True) or request.form or {}
    challenge_id = data.get('challenge_id')
    answer_text = (data.get('answer_text') or '').strip()
    response_time_ms = int(data.get('response_time_ms', 0))

    if not challenge_id:
        event = query_db("SELECT current_challenge_id FROM event WHERE id = 1", one=True)
        challenge_id = event['current_challenge_id'] if event else None

    if not challenge_id:
        return jsonify({"success": False, "error": "Missing challenge ID"}), 400

    try:
        challenge_id = int(challenge_id)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid challenge ID"}), 400

    is_corr, pts, msg = GameEngine.submit_answer(team_id, challenge_id, answer_text, response_time_ms)
    return jsonify({
        "success": True,
        "is_correct": is_corr,
        "points_awarded": pts,
        "message": msg
    })
