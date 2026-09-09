import time
import logging
from database import query_db, execute_db

logger = logging.getLogger('timer_manager')

class TimerManager:
    @staticmethod
    def start_timer(duration_sec, media_visibility_sec=15):
        """Start a new timer for duration_sec and media_visibility_sec."""
        now = time.time()
        execute_db("""
            UPDATE event 
            SET challenge_start_time = ?, 
                challenge_paused_at = NULL, 
                pause_accumulated_sec = 0, 
                challenge_duration_sec = ?,
                media_visibility_duration_sec = ?,
                status = 'ROUND_ACTIVE',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
        """, (now, duration_sec, media_visibility_sec))
        logger.info(f"Timer started: {duration_sec}s (media visibility: {media_visibility_sec}s)")

    @staticmethod
    def pause_timer():
        """Pause running timer."""
        event = query_db("SELECT * FROM event WHERE id = 1", one=True)
        if not event or not event['challenge_start_time'] or event['status'] == 'PAUSED':
            return False
        
        now = time.time()
        execute_db("""
            UPDATE event 
            SET challenge_paused_at = ?, 
                status = 'PAUSED',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
        """, (now,))
        logger.info("Timer paused.")
        return True

    @staticmethod
    def resume_timer():
        """Resume paused timer."""
        event = query_db("SELECT * FROM event WHERE id = 1", one=True)
        if not event or event['status'] != 'PAUSED' or not event['challenge_paused_at']:
            return False

        now = time.time()
        paused_duration = now - event['challenge_paused_at']
        new_accumulated = (event['pause_accumulated_sec'] or 0) + paused_duration

        execute_db("""
            UPDATE event 
            SET challenge_paused_at = NULL, 
                pause_accumulated_sec = ?, 
                status = 'ROUND_ACTIVE',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
        """, (new_accumulated,))
        logger.info(f"Timer resumed. Additional pause: {paused_duration:.2f}s")
        return True

    @staticmethod
    def extend_timer(seconds):
        """Extend current timer by given seconds."""
        event = query_db("SELECT * FROM event WHERE id = 1", one=True)
        if not event:
            return False
        
        current_dur = event['challenge_duration_sec'] or 0
        new_dur = max(0, current_dur + seconds)
        
        execute_db("""
            UPDATE event 
            SET challenge_duration_sec = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
        """, (new_dur,))
        logger.info(f"Timer adjusted by {seconds}s. New total: {new_dur}s")
        return True

    @staticmethod
    def get_remaining_sec():
        """Compute exact remaining seconds based on server time."""
        event = query_db("SELECT * FROM event WHERE id = 1", one=True)
        if not event or not event['challenge_start_time']:
            return 0, False, False # remaining, is_running, is_paused

        start_time = event['challenge_start_time']
        duration = event['challenge_duration_sec'] or 0
        accumulated_pause = event['pause_accumulated_sec'] or 0
        status = event['status']

        if status == 'PAUSED':
            paused_at = event['challenge_paused_at'] or time.time()
            elapsed = (paused_at - start_time) - accumulated_pause
            remaining = max(0, int(duration - elapsed))
            return remaining, False, True

        now = time.time()
        elapsed = (now - start_time) - accumulated_pause
        remaining = max(0, int(duration - elapsed))
        is_running = (remaining > 0 and status in ('ROUND_ACTIVE', 'FINAL_ACTIVE'))
        
        return remaining, is_running, False
        
    @staticmethod
    def get_media_timer():
        """Compute authoritative media visibility status and remaining seconds."""
        event = query_db("SELECT * FROM event WHERE id = 1", one=True)
        if not event or not event['challenge_start_time']:
            return {
                "visibility_duration": 0,
                "remaining": 0,
                "hide_at": None,
                "is_expired": True,
                "start_time": None,
                "pause_accumulated": 0
            }

        start_time = event['challenge_start_time']
        media_dur = event['media_visibility_duration_sec']
        if media_dur is None:
            media_dur = 15
        accumulated_pause = event['pause_accumulated_sec'] or 0
        status = event['status']

        if status == 'PAUSED':
            paused_at = event['challenge_paused_at'] or time.time()
            elapsed = (paused_at - start_time) - accumulated_pause
        else:
            now = time.time()
            elapsed = (now - start_time) - accumulated_pause

        remaining = max(0, int(round(media_dur - elapsed)))
        hide_at = start_time + media_dur + accumulated_pause
        is_expired = (elapsed >= media_dur)

        return {
            "visibility_duration": media_dur,
            "remaining": remaining,
            "hide_at": round(hide_at, 2),
            "is_expired": is_expired,
            "start_time": start_time,
            "pause_accumulated": accumulated_pause
        }
