/* TEAM MOBILE INTERFACE CONTROLLER JS */

let teamTimer = new ClientTimer('team-timer');
let currentChallengeStart = null;
let activeChallengeId = null;
let lastPhase = null;
let lastSubId = null;

function pollTeamState() {
    fetch('/api/state')
    .then(res => res.json())
    .then(state => {
        // Update score, rank, and status badges
        if (state.team) {
            const sEl = document.getElementById('team-score');
            if (sEl) sEl.textContent = state.team.score;

            const rEl = document.getElementById('team-rank');
            if (rEl) rEl.textContent = `#${state.team.rank || '-'}`;

            const stEl = document.getElementById('team-status');
            if (stEl) {
                stEl.textContent = state.team.status;
                stEl.className = `status-pill status-${state.team.status.toLowerCase()}`;
            }
        }

        // Timer update
        if (state.timer) {
            teamTimer.update(state.timer.remaining, state.timer.is_running, state.timer.is_paused);
        }

        // Track challenge start for response time calculation
        if (state.active_challenge && state.active_challenge.id !== activeChallengeId) {
            activeChallengeId = state.active_challenge.id;
            currentChallengeStart = Date.now();
        }

        // Re-render team content area if current_phase or submission state changed
        const currentSubId = state.team_submission ? state.team_submission.id : null;
        if (state.current_phase !== lastPhase || currentSubId !== lastSubId) {
            renderTeamContent(state);
            lastPhase = state.current_phase;
            lastSubId = currentSubId;
        }
    })
    .catch(err => console.error("Error polling team state:", err));
}

function renderTeamContent(state) {
    const area = document.getElementById('team-content-area');
    if (!area) return;

    const team = state.team || {};
    const phase = state.current_phase;
    const ch = state.active_challenge;
    const sub = state.team_submission;

    if (team.status === 'ELIMINATED') {
        area.innerHTML = `
            <div class="team-card eliminated-card">
                <div class="card-icon">💀</div>
                <h2 class="title-danger">TEAM ELIMINATED</h2>
                <p>Your team has been eliminated from active competition.</p>
                <div class="spectator-banner mt-3">
                    <h4>👀 SPECTATOR / AUDIENCE MODE ENABLED</h4>
                    <p>Follow live scores on the main projector display!</p>
                </div>
            </div>
        `;
        return;
    }

    if (phase === 'WINNER' && team.status === 'WINNER') {
        area.innerHTML = `
            <div class="team-card winner-card">
                <div class="card-icon">🏆</div>
                <h1 class="text-green">ESCAPE COMPLETE!</h1>
                <h2>VICTORY UNLOCKED</h2>
                <p>Congratulations! Your team is the Ultimate Champion!</p>
                <div class="prize-banner mt-3">FIRST PRIZE: ₹3,000 + CHAMPION TROPHY</div>
            </div>
        `;
        if (window.soundEngine) window.soundEngine.playVictory();
        return;
    }

    // RESULT REVEAL PHASE
    if (phase === 'RESULT' && ch) {
        let resultMsg = '';
        let resultClass = '';
        let soundToPlay = null;

        if (sub) {
            if (sub.is_correct) {
                resultMsg = `✅ CORRECT! +${sub.points_awarded} Points`;
                resultClass = 'text-green';
                soundToPlay = 'correct';
            } else {
                resultMsg = `❌ INCORRECT (${sub.points_awarded} Points)`;
                resultClass = 'text-danger';
                soundToPlay = 'wrong';
            }
        } else {
            resultMsg = `NO SUBMISSION RECORDED`;
            resultClass = 'text-muted';
        }

        area.innerHTML = `
            <div class="team-card result-reveal-card" style="border-color: var(--gold);">
                <span class="status-pill status-finalist">RESULT REVEAL</span>
                <h3 class="mt-3">${ch.title}</h3>
                
                <div class="result-box mt-3" style="background: rgba(0,0,0,0.8); padding: 20px; border-radius: 10px; border: 1px solid var(--border-hud);">
                    <div class="${resultClass}" style="font-size: 1.8rem; font-weight: bold;">
                        ${resultMsg}
                    </div>

                    <div class="mt-4 p-3" style="background: rgba(255,215,0,0.1); border: 1px dashed var(--gold); border-radius: 8px;">
                        <span style="color: var(--text-muted); font-size: 0.9rem;">OFFICIAL ANSWER:</span>
                        <h4 class="text-gold mt-1" style="font-size: 2rem; font-family: var(--font-title);">${ch.correct_answer}</h4>
                    </div>
                </div>
            </div>
        `;

        if (window.soundEngine && soundToPlay === 'correct') window.soundEngine.playCorrect();
        else if (window.soundEngine && soundToPlay === 'wrong') window.soundEngine.playWrong();
        return;
    }

    // ACTIVE CHALLENGE SUBMISSION PHASE
    if (ch && (phase === 'CHALLENGE' || phase === 'COUNTDOWN' || phase === 'FINAL_60')) {
        if (sub) {
            area.innerHTML = `
                <div class="team-card challenge-active-card">
                    <div class="challenge-header">
                        <span class="round-badge">ROUND ${state.current_round}</span>
                        <h3>${ch.title}</h3>
                        <div class="timer-row">
                            <span>TIME REMAINING:</span>
                            <strong class="timer-digits text-warning" id="team-timer">--:--</strong>
                        </div>
                    </div>

                    <div class="submission-locked-box">
                        <div class="lock-icon">🔒</div>
                        <h4>SUBMISSION LOCKED & RECORDED</h4>
                        <p>Your Answer: <code>${sub.answer_text}</code></p>
                        <span class="text-muted">Awaiting host result reveal...</span>
                    </div>
                </div>
            `;
            return;
        }

        // Render Answer Input Controls
        let inputControls = '';
        if (ch.challenge_type === 'NO_SUBMISSION_TRAP') {
            inputControls = `
                <div class="alert alert-warning">⚠️ TRAP ALERT: Read projector prompt carefully!</div>
                <button onclick="submitTeamAnswer('PANIC_SUBMIT')" class="btn-danger btn-full">SUBMIT ANSWER NOW (RISK)</button>
            `;
        } else if (ch.challenge_type === 'GAMBLE_WAGER') {
            inputControls = `
                <div class="wager-options-grid">
                    <button onclick="submitTeamAnswer('SAFE')" class="wager-btn safe-wager"><strong>SAFE</strong><br>1x Normal Points (0 Penalty)</button>
                    <button onclick="submitTeamAnswer('RISK')" class="wager-btn risk-wager"><strong>RISK</strong><br>2x Points (-10 Loss Penalty)</button>
                    <button onclick="submitTeamAnswer('ALL_IN')" class="wager-btn allin-wager"><strong>ALL-IN</strong><br>3x Points (-25 Loss Penalty)</button>
                </div>
            `;
        } else if (ch.options_json && ch.options_json !== '[]') {
            try {
                const opts = JSON.parse(ch.options_json);
                inputControls = `
                    <div class="options-grid">
                        ${opts.map(opt => `<button onclick="submitTeamAnswer('${opt}')" class="btn-cyan btn-option">${opt}</button>`).join('')}
                    </div>
                `;
            } catch(e) {
                inputControls = renderTextInputBox();
            }
        } else {
            inputControls = renderTextInputBox();
        }

        area.innerHTML = `
            <div class="team-card challenge-active-card">
                <div class="challenge-header">
                    <span class="round-badge">ROUND ${state.current_round}</span>
                    <h3>${ch.title}</h3>
                    <div class="timer-row">
                        <span>TIME REMAINING:</span>
                        <strong class="timer-digits text-warning" id="team-timer">--:--</strong>
                    </div>
                </div>

                <div class="challenge-desc"><p>${ch.description}</p></div>
                <div class="answer-form-container">${inputControls}</div>
            </div>
        `;
        return;
    }

    // DEFAULT WAITING SCREEN
    area.innerHTML = `
        <div class="team-card waiting-card">
            <div class="pulse-ring"></div>
            <h3>WAITING FOR HOST...</h3>
            <p>The host is preparing the next challenge or mission.</p>
            <div class="hud-spinner mt-3"></div>
        </div>
    `;
}

function renderTextInputBox() {
    return `
        <div class="text-input-box">
            <input type="text" id="answer-input" placeholder="Type answer code..." class="input-hud-large" autocomplete="off">
            <button onclick="submitFromInput()" class="btn-green btn-full mt-3">SUBMIT ANSWER</button>
        </div>
    `;
}

function submitTeamAnswer(answerText) {
    if (!activeChallengeId) {
        alert("No active challenge to submit to.");
        return;
    }

    const responseTimeMs = currentChallengeStart ? (Date.now() - currentChallengeStart) : 0;

    fetch('/team/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            challenge_id: activeChallengeId,
            answer_text: answerText,
            response_time_ms: responseTimeMs
        })
    })
    .then(res => res.json())
    .then(data => {
        if (!data.success) {
            alert('Submission error: ' + (data.error || 'Unknown Error'));
        } else {
            if (window.soundEngine) {
                if (data.is_correct) window.soundEngine.playCorrect();
                else window.soundEngine.playWrong();
            }
            pollTeamState();
        }
    })
    .catch(err => console.error('Submission request failed:', err));
}

function submitFromInput() {
    const input = document.getElementById('answer-input');
    if (input && input.value.trim().length > 0) {
        submitTeamAnswer(input.value.trim());
    } else {
        alert("Please enter an answer before submitting.");
    }
}

// Start 1-second polling loop
setInterval(pollTeamState, 1000);
pollTeamState();
