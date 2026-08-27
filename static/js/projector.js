/* ═══════════════════════════════════════════════════════════════
   PROJECTOR DISPLAY CONTROLLER — HORROR EDITION
   "The screen watches you."
   ═══════════════════════════════════════════════════════════════ */

let projectorTimer = new ClientTimer('proj-timer');
let lastPhase = null;
let lastChallengeId = null;
let heartbeatActive = false;
let flashIntervalId = null;

/* ────────────────────────────────────────────────
   RED FLASH SYSTEM
   ──────────────────────────────────────────────── */

function triggerRedFlash(duration = 600) {
    const flash = document.getElementById('horror-flash');
    if (!flash) return;
    flash.classList.remove('flash-active', 'pulse-active');
    // Force reflow to restart animation
    void flash.offsetWidth;
    flash.classList.add('flash-active');
    setTimeout(() => flash.classList.remove('flash-active'), duration);
}

function startRedPulse() {
    const flash = document.getElementById('horror-flash');
    if (!flash) return;
    flash.classList.remove('flash-active');
    flash.classList.add('pulse-active');
}

function stopRedPulse() {
    const flash = document.getElementById('horror-flash');
    if (!flash) return;
    flash.classList.remove('pulse-active', 'flash-active');
}

function startPeriodicFlash(intervalMs = 10000) {
    stopPeriodicFlash();
    flashIntervalId = setInterval(() => {
        triggerRedFlash(400);
    }, intervalMs);
}

function stopPeriodicFlash() {
    if (flashIntervalId) {
        clearInterval(flashIntervalId);
        flashIntervalId = null;
    }
}

/* ────────────────────────────────────────────────
   POLL + RENDER
   ──────────────────────────────────────────────── */

function pollProjectorState() {
    fetch('/api/state')
    .then(res => res.json())
    .then(state => {
        const viewport = document.getElementById('projector-viewport');
        if (viewport) {
            viewport.className = 'projector-viewport ' + getRoundThemeClass(state.current_round);
        }

        // Update top HUD
        const rBadge = document.getElementById('proj-round-badge');
        if (rBadge) rBadge.textContent = state.round_title || `ROUND ${state.current_round}`;

        if (state.timer) {
            projectorTimer.update(state.timer.remaining, state.timer.is_running, state.timer.is_paused);
        }

        // Render stage if phase or active challenge changed
        if (state.current_phase !== lastPhase || (state.active_challenge && state.active_challenge.id !== lastChallengeId)) {
            // Cleanup previous phase effects
            if (lastPhase === 'FINAL_60' && state.current_phase !== 'FINAL_60') {
                stopRedPulse();
                stopPeriodicFlash();
                if (window.soundEngine) window.soundEngine.stopHeartbeat();
                heartbeatActive = false;
            }

            renderProjectorStage(state);
            lastPhase = state.current_phase;
            if (state.active_challenge) lastChallengeId = state.active_challenge.id;
        }
    })
    .catch(err => console.error("Projector state poll error:", err));
}

function getRoundThemeClass(roundNum) {
    if (roundNum === 1) return 'theme-r1';
    if (roundNum === 2) return 'theme-r2';
    if (roundNum === 3) return 'theme-r3';
    if (roundNum >= 4) return 'theme-final';
    return 'theme-r1';
}

function renderProjectorStage(state) {
    const stage = document.getElementById('projector-stage');
    if (!stage) return;

    const phase = state.current_phase;
    const ch = state.active_challenge;

    if (phase === 'INTRO') {
        stage.innerHTML = `
            <div class="proj-intro-box">
                <h1 class="glitch-title">ESCAPE THE ROOM</h1>
                <h2 class="subtitle" style="color: var(--text-bone); opacity: 0.8; letter-spacing: 5px;">THE FINAL 60</h2>
                <p class="mt-4" style="font-size: clamp(1.3rem, 2.3vw, 2rem); color: var(--text-ash); font-family: var(--font-oswald); letter-spacing: 3px;">50 TEAMS ● 3 ROUNDS ● 1 SURVIVOR</p>
                <div class="network-info-panel mt-4">
                    <p style="font-size: 1.1rem; color: var(--text-ghost); font-family: var(--font-oswald);">TEAM LEADER — ENTER IF YOU DARE:</p>
                    <div class="ip-badge">http://${state.local_ip}:${state.port}/team/login</div>
                </div>
            </div>
        `;
    } else if (phase === 'ROUND_INTRO') {
        triggerRedFlash(800);
        if (window.soundEngine) window.soundEngine.playWarning();

        stage.innerHTML = `
            <div class="proj-intro-box">
                <span class="hud-round-badge">ROUND ${state.current_round}</span>
                <h1 class="mt-3" style="font-size: clamp(2.5rem, 5vw, 5rem); color: var(--crimson); text-shadow: var(--glow-crimson);">${state.round_title}</h1>
                <p style="font-size: clamp(1.4rem, 2.8vw, 2.5rem); color: var(--text-bone); font-family: var(--font-oswald); letter-spacing: 3px;" class="mt-3">SURVIVING TEAMS: ${state.active_teams_count}</p>
            </div>
        `;
    } else if (phase === 'CHALLENGE' || phase === 'COUNTDOWN') {
        if (!ch) return;

        let displayContent = '';
        try {
            const data = JSON.parse(ch.display_data_json || '{}');

            if (ch.challenge_type === 'SPEED_TEST') {
                displayContent = `
                    <div class="proj-visual-container">
                        <p style="color: var(--text-ghost); font-size: 1.1rem; margin-bottom: 1.5vh; font-family: var(--font-oswald); letter-spacing: 2px;">MEMORIZE BEFORE IT VANISHES FOREVER</p>
                        <div class="speed-test-shapes-grid">
                            <div class="shape-pill">▲ 7 TRIANGLES</div>
                            <div class="shape-pill">● 4 CIRCLES</div>
                            <div class="shape-pill">■ 6 SQUARES</div>
                            <div class="shape-pill">★ 3 STARS</div>
                        </div>
                    </div>
                `;
            } else if (ch.challenge_type === 'NUMBER_PATTERN') {
                displayContent = `
                    <div class="proj-visual-container">
                        <div class="pattern-sequence-box">${data.sequence || '2 → 6 → 12 → 20 → 30 → ?'}</div>
                        <p style="color: var(--blood-bright); font-size: 1.3rem; margin-top: 2vh; font-family: var(--font-oswald);">HINT: The pattern hides in the differences...</p>
                    </div>
                `;
            } else if (ch.challenge_type === 'NO_SUBMISSION_TRAP') {
                triggerRedFlash(500);
                displayContent = `
                    <div class="proj-visual-container" style="border-color: var(--crimson);">
                        <div class="trap-warning-strip">
                            <div class="trap-warning-text">⚠ DO NOT ANSWER THIS QUESTION ⚠</div>
                        </div>
                        <p style="font-size: clamp(2rem, 4vw, 4rem); color: var(--text-bone); font-family: var(--font-horror); margin-top: 1.5vh;">What is 5 + 5?</p>
                        <p style="color: var(--crimson); font-size: 1.2rem; margin-top: 1vh; font-family: var(--font-oswald);">ANY SUBMISSION = IMMEDIATE 10-POINT PENALTY</p>
                    </div>
                `;
            } else if (ch.challenge_type === 'PROJECTOR_GLITCH') {
                displayContent = `
                    <div class="proj-visual-container" style="border-color: var(--crimson);">
                        <p style="color: var(--blood-bright); font-size: 1.4rem; font-family: var(--font-horror); letter-spacing: 3px;">SYSTEM CORRUPTION 0x884</p>
                        <div class="glitch-code-box">${data.glitch_text || 'E 7 S C 2 A P 9 E'}</div>
                        <p style="color: var(--text-bone); font-size: 1.2rem; font-family: var(--font-oswald);">Filter out the noise. Find the hidden word.</p>
                    </div>
                `;
            } else if (ch.challenge_type === 'SECRET_MATRIX') {
                displayContent = `
                    <div class="proj-visual-container">
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; font-family: var(--font-mono); font-size: 2.8rem; color: var(--blood-bright);">
                            ${['C','A','T','A','R','E','R','E','A','D','Y','!'].map(letter => `
                                <div style="background: rgba(139,0,0,0.1); padding: 12px 24px; border: 1px solid var(--blood); box-shadow: var(--glow-dim);">${letter}</div>
                            `).join('')}
                        </div>
                    </div>
                `;
            } else if (ch.challenge_type === 'INVESTIGATION') {
                displayContent = `
                    <div class="proj-visual-container" style="border-color: var(--crimson);">
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; width: 90%;">
                            <div style="background: rgba(139,0,0,0.08); border: 1px solid var(--blood); padding: 18px; border-radius: 4px; text-align: left;">
                                <h4 style="color: var(--crimson); font-size: 1.4rem; font-family: var(--font-horror);">SUSPECT A</h4>
                                <p style="font-size: 1.1rem; color: var(--text-bone); margin-top: 8px; font-family: var(--font-type);">"I entered classroom at 8:10."</p>
                            </div>
                            <div style="background: rgba(139,0,0,0.08); border: 1px solid var(--blood); padding: 18px; border-radius: 4px; text-align: left;">
                                <h4 style="color: var(--crimson); font-size: 1.4rem; font-family: var(--font-horror);">SUSPECT B</h4>
                                <p style="font-size: 1.1rem; color: var(--text-bone); margin-top: 8px; font-family: var(--font-type);">"I saw Person C near projector at 8:12."</p>
                            </div>
                            <div style="background: rgba(139,0,0,0.08); border: 1px solid var(--blood); padding: 18px; border-radius: 4px; text-align: left;">
                                <h4 style="color: var(--crimson); font-size: 1.4rem; font-family: var(--font-horror);">SUSPECT C</h4>
                                <p style="font-size: 1.1rem; color: var(--text-bone); margin-top: 8px; font-family: var(--font-type);">"I never entered room today."</p>
                            </div>
                        </div>
                        <p style="color: var(--blood-bright); font-size: 1.6rem; margin-top: 2vh; font-family: var(--font-horror); letter-spacing: 2px;">THE CLOCK READ 8:15 — WHO IS THE LIAR?</p>
                    </div>
                `;
            } else {
                displayContent = `
                    <div class="proj-visual-container">
                        <p style="font-size: clamp(1.5rem, 2.8vw, 2.8rem); color: var(--blood-bright); font-family: var(--font-horror); letter-spacing: 2px;">${data.prompt || data.question || ch.description}</p>
                    </div>
                `;
            }
        } catch(e) {
            displayContent = `<div class="proj-visual-container"><p style="font-size: 2rem; color: var(--text-bone);">${ch.description}</p></div>`;
        }

        stage.innerHTML = `
            <div class="proj-challenge-box animate-fade-in-up">
                <div class="proj-challenge-header">
                    <span class="hud-round-badge">CHALLENGE ${ch.order_index}</span>
                    <h1 class="proj-challenge-title">${ch.title}</h1>
                    <p class="proj-challenge-desc">${ch.description}</p>
                </div>
                ${displayContent}
            </div>
        `;
    } else if (phase === 'RESULT') {
        const stats = state.result_stats || {};
        const ch = state.active_challenge || {};
        const fastest = stats.fastest_team ? `${stats.fastest_team.team_name} (${(stats.fastest_team.response_time_ms/1000).toFixed(1)}s)` : 'None';

        // Flash if many wrong answers
        if (stats.wrong_count > stats.correct_count) {
            triggerRedFlash(600);
        }

        stage.innerHTML = `
            <div class="proj-challenge-box animate-fade-in-up" style="border-color: var(--blood-bright);">
                <div class="proj-challenge-header">
                    <span class="hud-round-badge" style="background: rgba(139,0,0,0.3); color: var(--blood-bright);">VERDICT</span>
                    <h1 class="proj-challenge-title">${ch.title || 'CHALLENGE COMPLETE'}</h1>
                </div>

                <div class="proj-visual-container animate-fade-in-up" style="border-color: var(--blood); width: 90%; animation-delay: 0.2s; flex: 1; display: flex; flex-direction: column; justify-content: center;">
                    <p style="color: var(--text-ghost); font-size: 1.2rem; font-family: var(--font-oswald); letter-spacing: 2px;">THE CORRECT ANSWER WAS</p>
                    <div style="font-family: var(--font-horror); font-size: clamp(4rem, 8vw, 8rem); color: var(--blood-bright); text-shadow: var(--glow-blood); margin: 2vh 0; animation: horrorFlicker 3s infinite;">
                        ${ch.correct_answer || stats.correct_answer || 'N/A'}
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 2vw; width: 90%; margin-top: auto; padding-top: 2vh;" class="animate-fade-in-up" style="animation-delay: 0.4s;">
                    <div style="background: rgba(58,90,58,0.08); border: 1px solid #3a5a3a; padding: 2vh; border-radius: 4px; display: flex; flex-direction: column; justify-content: center; align-items: center; box-shadow: inset 0 0 20px rgba(58,90,58,0.2);">
                        <span style="color: #5a8a5a; font-size: 1.2rem; font-family: var(--font-oswald); font-weight: 600; letter-spacing: 1px;">SURVIVED</span>
                        <div style="font-size: 3rem; color: var(--text-bone); font-family: var(--font-horror); text-shadow: 0 0 10px rgba(90,138,90,0.5);">${stats.correct_count || 0}</div>
                    </div>
                    <div style="background: rgba(139,0,0,0.1); border: 1px solid var(--blood); padding: 2vh; border-radius: 4px; display: flex; flex-direction: column; justify-content: center; align-items: center; box-shadow: inset 0 0 20px rgba(139,0,0,0.3);">
                        <span style="color: var(--crimson); font-size: 1.2rem; font-family: var(--font-oswald); font-weight: 600; letter-spacing: 1px;">FAILED</span>
                        <div style="font-size: 3rem; color: var(--text-bone); font-family: var(--font-horror); text-shadow: var(--glow-dim);">${stats.wrong_count || 0}</div>
                    </div>
                    <div style="background: rgba(139,0,0,0.05); border: 1px solid var(--border-rust); padding: 2vh; border-radius: 4px; display: flex; flex-direction: column; justify-content: center; align-items: center; box-shadow: inset 0 0 20px rgba(0,0,0,0.5);">
                        <span style="color: var(--text-ash); font-size: 1.2rem; font-family: var(--font-oswald); font-weight: 600; letter-spacing: 1px;">⚡ FASTEST</span>
                        <div style="font-size: 1.6rem; color: var(--text-bone); font-family: var(--font-oswald); margin-top: 5px; text-shadow: 0 0 10px rgba(212,197,176,0.3);">${fastest}</div>
                    </div>
                </div>
            </div>
        `;
        if (window.soundEngine) window.soundEngine.playCorrect();
    } else if (phase === 'FINAL_60') {
        // START THE HORROR — heartbeat + periodic red flash
        if (!heartbeatActive) {
            if (window.soundEngine) window.soundEngine.startHeartbeat();
            heartbeatActive = true;
        }
        startRedPulse();
        startPeriodicFlash(8000);

        stage.innerHTML = `
            <div class="final-60-aura">
                <h1 style="color: var(--crimson); font-size: clamp(2.5rem, 5vw, 5rem); font-family: var(--font-horror); text-shadow: var(--glow-crimson); letter-spacing: 5px;">THE FINAL 60 SECONDS</h1>
                <p style="font-size: clamp(1.2rem, 2.3vw, 2.3rem); color: var(--text-bone); font-family: var(--font-oswald); letter-spacing: 3px;" class="mt-2">TOP 5 FINALISTS: ENTER THE MASTER CODE... OR DIE TRYING</p>
                <div class="final-60-timer-digits mt-3" id="final-60-timer">60</div>
            </div>
        `;
    } else if (phase === 'ELIMINATION' || phase === 'ELIMINATED') {
        // JUMP SCARE on elimination
        triggerRedFlash(1500);
        if (window.soundEngine) window.soundEngine.playElimination();

        fetch('/api/leaderboard')
        .then(res => res.json())
        .then(lb => {
            const safeTeams = lb.filter(t => t.status !== 'ELIMINATED');
            const elimTeams = lb.filter(t => t.status === 'ELIMINATED');

            stage.innerHTML = `
                <div class="proj-elimination-grid">
                    <div class="proj-elim-card proj-safe">
                        <h2 style="color: #5a8a5a; text-shadow: 0 0 12px rgba(58,90,58,0.3);">☠ SURVIVORS (${safeTeams.length})</h2>
                        <div class="proj-team-list">
                            ${safeTeams.map(t => `
                                <div class="proj-team-item safe-item">
                                    <span>Rank #${t.rank} — <strong>${t.team_name}</strong></span>
                                    <span style="color: #5a8a5a;">${t.score} pts</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    <div class="proj-elim-card proj-danger">
                        <h2 style="color: var(--crimson); text-shadow: var(--glow-crimson);">💀 ELIMINATED (${elimTeams.length})</h2>
                        <div class="proj-team-list">
                            ${elimTeams.map(t => `
                                <div class="proj-team-item elim-item">
                                    <span>Rank #${t.rank} — <strong>${t.team_name}</strong></span>
                                    <span>${t.score} pts</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            `;
        });
    } else if (phase === 'WINNER') {
        stopRedPulse();
        stopPeriodicFlash();
        if (window.soundEngine) {
            window.soundEngine.stopHeartbeat();
            window.soundEngine.playVictory();
        }
        heartbeatActive = false;

        fetch('/api/state')
        .then(res => res.json())
        .then(st => {
            stage.innerHTML = `
                <div class="winner-climax-box">
                    <h1 class="glitch-title">YOU HAVE ESCAPED</h1>
                    <h2 style="color: var(--text-bone); font-size: clamp(1.8rem, 3.5vw, 3.5rem); margin-top: 10px; font-family: var(--font-oswald); letter-spacing: 4px; opacity: 0.8;">THE NIGHTMARE IS OVER</h2>
                    <div class="winner-team-name">🏆 ULTIMATE SURVIVOR 🏆</div>
                    <div class="prize-banner mt-4">FIRST PRIZE: ₹3,000 + CHAMPION TROPHY</div>
                </div>
            `;
        });
    } else if (phase === 'LEADERBOARD') {
        fetch('/api/leaderboard')
        .then(res => res.json())
        .then(lb => {
            stage.innerHTML = `
                <div class="proj-challenge-box" style="width: 85%; border-color: var(--blood);">
                    <h1 style="color: var(--crimson); font-size: 3rem; font-family: var(--font-horror); text-shadow: var(--glow-crimson);">KILL ORDER</h1>
                    <table class="hud-table" style="font-size: 1.4rem;">
                        <thead>
                            <tr><th>RANK</th><th>TEAM</th><th>SCORE</th><th>FATE</th></tr>
                        </thead>
                        <tbody>
                            ${lb.slice(0, 10).map(t => `
                                <tr>
                                    <td><strong>#${t.rank}</strong></td>
                                    <td>${t.team_name}</td>
                                    <td><strong style="color: var(--blood-bright);">${t.score} pts</strong></td>
                                    <td><span class="status-pill status-${t.status.toLowerCase()}">${t.status}</span></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        });
    }
}

// Start 1-second polling loop
setInterval(pollProjectorState, 1000);
pollProjectorState();
