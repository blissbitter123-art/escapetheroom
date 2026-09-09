-- Escape The Room: The Final 60 Database Schema

CREATE TABLE IF NOT EXISTS event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name TEXT NOT NULL DEFAULT 'ESCAPE THE ROOM: THE FINAL 60',
    status TEXT NOT NULL DEFAULT 'IDLE', -- IDLE, ROUND_ACTIVE, PAUSED, ROUND_COMPLETE, FINAL_ACTIVE, ENDED
    current_round INTEGER NOT NULL DEFAULT 1, -- 1 (R1), 2 (R2), 3 (R3), 4 (Final 60)
    current_challenge_id INTEGER DEFAULT NULL,
    current_phase TEXT NOT NULL DEFAULT 'INTRO', -- INTRO, ROUND_INTRO, CHALLENGE, COUNTDOWN, WARNING, RESULT, LEADERBOARD, ELIMINATION, FINAL_60, WINNER
    challenge_start_time REAL DEFAULT NULL,
    challenge_paused_at REAL DEFAULT NULL,
    pause_accumulated_sec REAL DEFAULT 0,
    challenge_duration_sec INTEGER DEFAULT 0,
    media_visibility_duration_sec INTEGER DEFAULT 15,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rounds (
    id INTEGER PRIMARY KEY,
    round_number INTEGER UNIQUE NOT NULL,
    title TEXT NOT NULL,
    subtitle TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, IN_PROGRESS, COMPLETED
    start_team_count INTEGER NOT NULL,
    end_team_count INTEGER NOT NULL,
    target_duration_min INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_number INTEGER UNIQUE NOT NULL,
    team_name TEXT NOT NULL,
    pin TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, ELIMINATED, FINALIST, WINNER
    score INTEGER NOT NULL DEFAULT 0,
    rank INTEGER DEFAULT NULL,
    round3_wager_type TEXT DEFAULT NULL, -- SAFE, RISK, ALL_IN
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS challenges (
    id INTEGER PRIMARY KEY,
    round_id INTEGER NOT NULL,
    mission_id INTEGER DEFAULT 1,
    challenge_key TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    challenge_type TEXT NOT NULL, -- SPEED_TEST, NUMBER_PATTERN, NO_SUBMISSION_TRAP, MEMORY_ATTACK, SECRET_MATRIX, CLASSROOM_OBSERVATION, MULTI_STEP_TRAP, CORRECTION_WINDOW, HOST_STORY, INVESTIGATION, PROJECTOR_GLITCH, CIPHER_ROOM, DOUBLE_AGENT, LOCK_CHAIN, GAMBLE_WAGER, FINAL_60
    duration_sec INTEGER NOT NULL DEFAULT 60,
    correct_answer TEXT,
    expected_action TEXT DEFAULT 'SUBMIT_ANSWER', -- SUBMIT_ANSWER, NO_SUBMISSION, SELECT_OPTION, ENTER_CODE, CHOOSE_WAGER
    base_points INTEGER NOT NULL DEFAULT 10,
    speed_bonus_points INTEGER NOT NULL DEFAULT 0,
    penalty_points INTEGER NOT NULL DEFAULT 0,
    difficulty TEXT NOT NULL DEFAULT 'EASY', -- EASY, MEDIUM, HARD, MONSTER
    display_data_json TEXT,
    options_json TEXT,
    media_visibility_duration_sec INTEGER DEFAULT 15,
    order_index INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (round_id) REFERENCES rounds (id)
);

CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    challenge_id INTEGER NOT NULL,
    answer_text TEXT,
    is_correct INTEGER NOT NULL DEFAULT 0,
    points_awarded INTEGER NOT NULL DEFAULT 0,
    response_time_ms INTEGER DEFAULT 0,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    override_by_host INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (team_id) REFERENCES teams (id),
    FOREIGN KEY (challenge_id) REFERENCES challenges (id)
);

CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    round_id INTEGER NOT NULL,
    challenge_id INTEGER,
    points_delta INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams (id)
);

CREATE TABLE IF NOT EXISTS eliminations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    round_id INTEGER NOT NULL,
    eliminated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    rank_at_elimination INTEGER,
    restored_at TIMESTAMP DEFAULT NULL,
    reason TEXT NOT NULL,
    FOREIGN KEY (team_id) REFERENCES teams (id)
);

CREATE TABLE IF NOT EXISTS wagers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    challenge_id INTEGER NOT NULL,
    wager_type TEXT NOT NULL, -- SAFE, RISK, ALL_IN
    multiplier REAL NOT NULL DEFAULT 1.0,
    penalty INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams (id),
    FOREIGN KEY (challenge_id) REFERENCES challenges (id)
);

CREATE TABLE IF NOT EXISTS event_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    description TEXT NOT NULL,
    team_id INTEGER DEFAULT NULL,
    payload_json TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS challenge_clues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenge_id INTEGER NOT NULL,
    clue_text TEXT NOT NULL,
    cost_points INTEGER NOT NULL DEFAULT 5,
    order_index INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (challenge_id) REFERENCES challenges (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS clue_purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    clue_id INTEGER NOT NULL,
    challenge_id INTEGER NOT NULL,
    points_spent INTEGER NOT NULL,
    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams (id),
    FOREIGN KEY (clue_id) REFERENCES challenge_clues (id) ON DELETE CASCADE,
    FOREIGN KEY (challenge_id) REFERENCES challenges (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS challenge_media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenge_id INTEGER NOT NULL,
    media_type TEXT NOT NULL DEFAULT 'IMAGE',
    file_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    display_duration_sec INTEGER NOT NULL DEFAULT 10, -- seconds this media stays on the projector (0 = play video to the end)
    order_index INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (challenge_id) REFERENCES challenges (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_teams_status ON teams(status);
CREATE INDEX IF NOT EXISTS idx_teams_score ON teams(score DESC);
CREATE INDEX IF NOT EXISTS idx_submissions_team ON submissions(team_id);
CREATE INDEX IF NOT EXISTS idx_submissions_challenge ON submissions(challenge_id);
CREATE INDEX IF NOT EXISTS idx_logs_created ON event_logs(created_at DESC);
