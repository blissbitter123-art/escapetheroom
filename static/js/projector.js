/* PROJECTOR DISPLAY CONTROLLER JS — STAGE RENDERER */

let projectorTimer = new ClientTimer('proj-timer');
let lastPhase = null;
let lastChallengeId = null;

function pollProjectorState() {
    fetch('/api/state')
    .then(res => res.json())
    .then(state => {
        const viewport = document.getElementById('projector-viewport');
        if (viewport) {
            // Apply round color theme class
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
                <h2 class="subtitle">THE FINAL 60</h2>
                <p class="mt-4 text-cyan" style="font-size: clamp(1.4rem, 2.5vw, 2.2rem);">50 TEAMS ● 3 ROUNDS ● 1 WINNER</p>
                <div class="network-info-panel mt-4">
                    <p style="font-size: 1.2rem; color: var(--text-muted);">TEAM LEADER MOBILE CONNECT URL:</p>
                    <div class="ip-badge">http://${state.local_ip}:${state.port}/team/login</div>
                </div>
            </div>
        `;
    } else if (phase === 'ROUND_INTRO') {
        stage.innerHTML = `
            <div class="proj-intro-box">
                <span class="hud-round-badge">ROUND ${state.current_round}</span>
                <h1 class="mt-3" style="font-size: clamp(2.5rem, 5vw, 5rem);">${state.round_title}</h1>
                <p style="font-size: clamp(1.6rem, 3vw, 2.8rem); color: var(--gold);" class="mt-3">ACTIVE SURVIVING TEAMS: ${state.active_teams_count}</p>
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
                        <p style="color: var(--text-muted); font-size: 1.2rem; margin-bottom: 1.5vh;">PATTERN VISUAL (DISAPPEARS IN 15 SECONDS)</p>
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
                        <p style="color: var(--gold); font-size: 1.4rem; margin-top: 2vh;">HINT: Examine the incremental differences between numbers.</p>
                    </div>
                `;
            } else if (ch.challenge_type === 'NO_SUBMISSION_TRAP') {
                displayContent = `
                    <div class="proj-visual-container" style="border-color: var(--red);">
                        <div class="trap-warning-strip">
                            <div class="trap-warning-text">⚠️ DO NOT ANSWER THIS QUESTION ⚠️</div>
                        </div>
                        <p style="font-size: clamp(2rem, 4vw, 4rem); color: #fff; font-family: var(--font-title); margin-top: 1.5vh;">What is 5 + 5?</p>
                        <p style="color: var(--red); font-size: 1.3rem; margin-top: 1vh;">WARNING: Any submission results in an immediate 10-point penalty!</p>
                    </div>
                `;
            } else if (ch.challenge_type === 'PROJECTOR_GLITCH') {
                displayContent = `
                    <div class="proj-visual-container" style="border-color: var(--magenta);">
                        <p style="color: var(--magenta); font-size: 1.5rem; font-family: var(--font-title);">SYSTEM ERROR 0x884</p>
                        <div class="glitch-code-box">${data.glitch_text || 'E 7 S C 2 A P 9 E'}</div>
                        <p style="color: #fff; font-size: 1.3rem;">Filter out numeric noise digits to unlock password.</p>
                    </div>
                `;
            } else if (ch.challenge_type === 'SECRET_MATRIX') {
                displayContent = `
                    <div class="proj-visual-container">
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; font-family: var(--font-mono); font-size: 3rem; color: var(--cyan);">
                            <div style="background: #111; padding: 15px 30px; border: 1px solid var(--cyan);">C</div>
                            <div style="background: #111; padding: 15px 30px; border: 1px solid var(--cyan);">A</div>
                            <div style="background: #111; padding: 15px 30px; border: 1px solid var(--cyan);">T</div>
                            <div style="background: #111; padding: 15px 30px; border: 1px solid var(--cyan);">A</div>
                            <div style="background: #111; padding: 15px 30px; border: 1px solid var(--cyan);">R</div>
                            <div style="background: #111; padding: 15px 30px; border: 1px solid var(--cyan);">E</div>
                            <div style="background: #111; padding: 15px 30px; border: 1px solid var(--cyan);">R</div>
                            <div style="background: #111; padding: 15px 30px; border: 1px solid var(--cyan);">E</div>
                            <div style="background: #111; padding: 15px 30px; border: 1px solid var(--cyan);">A</div>
                            <div style="background: #111; padding: 15px 30px; border: 1px solid var(--cyan);">D</div>
                            <div style="background: #111; padding: 15px 30px; border: 1px solid var(--cyan);">Y</div>
                            <div style="background: #111; padding: 15px 30px; border: 1px solid var(--cyan);">!</div>
                        </div>
                    </div>
                `;
            } else if (ch.challenge_type === 'INVESTIGATION') {
                displayContent = `
                    <div class="proj-visual-container" style="border-color: var(--magenta);">
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; width: 90%;">
                            <div style="background: rgba(255,0,85,0.1); border: 1px solid var(--magenta); padding: 20px; border-radius: 10px; text-align: left;">
                                <h4 style="color: var(--magenta); font-size: 1.5rem;">PERSON A</h4>
                                <p style="font-size: 1.2rem; color: #fff; margin-top: 10px;">"I entered classroom at 8:10."</p>
                            </div>
                            <div style="background: rgba(255,0,85,0.1); border: 1px solid var(--magenta); padding: 20px; border-radius: 10px; text-align: left;">
                                <h4 style="color: var(--magenta); font-size: 1.5rem;">PERSON B</h4>
                                <p style="font-size: 1.2rem; color: #fff; margin-top: 10px;">"I saw Person C near projector at 8:12."</p>
                            </div>
                            <div style="background: rgba(255,0,85,0.1); border: 1px solid var(--magenta); padding: 20px; border-radius: 10px; text-align: left;">
                                <h4 style="color: var(--magenta); font-size: 1.5rem;">PERSON C</h4>
                                <p style="font-size: 1.2rem; color: #fff; margin-top: 10px;">"I never entered room today."</p>
                            </div>
                        </div>
                        <p style="color: var(--gold); font-size: 1.8rem; margin-top: 2vh;">PROJECTOR CLOCK: 8:15 — WHO IS LYING?</p>
                    </div>
                `;
            } else {
                displayContent = `
                    <div class="proj-visual-container">
                        <p style="font-size: clamp(1.6rem, 3vw, 3rem); color: var(--accent, var(--cyan)); font-family: var(--font-title);">${data.prompt || data.question || ch.description}</p>
                    </div>
                `;
            }
        } catch(e) {
            displayContent = `<div class="proj-visual-container"><p style="font-size: 2rem;">${ch.description}</p></div>`;
        }

        stage.innerHTML = `
            <div class="proj-challenge-box">
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

        stage.innerHTML = `
            <div class="proj-challenge-box" style="border-color: var(--gold); height: 72vh;">
                <div class="proj-challenge-header">
                    <span class="hud-round-badge" style="background: var(--gold); color: #000;">RESULT REVEAL</span>
                    <h1 class="proj-challenge-title" style="color: var(--gold);">${ch.title || 'CHALLENGE COMPLETE'}</h1>
                </div>

                <div class="proj-visual-container" style="border-color: var(--gold); background: rgba(0,0,0,0.85); width: 90%;">
                    <p style="color: var(--text-muted); font-size: 1.3rem;">OFFICIAL CORRECT ANSWER</p>
                    <div style="font-family: var(--font-title); font-size: clamp(3rem, 6vw, 6rem); color: var(--gold); text-shadow: var(--gold-glow); margin: 1vh 0;">
                        ${ch.correct_answer || stats.correct_answer || 'N/A'}
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 2vw; width: 90%;">
                    <div style="background: rgba(0,255,102,0.1); border: 2px solid var(--green); padding: 1.5vh; border-radius: 12px;">
                        <span style="color: var(--green); font-size: 1.1rem; font-weight: bold;">CORRECT TEAMS</span>
                        <div style="font-size: 2.5rem; color: #fff; font-weight: 900;">${stats.correct_count || 0}</div>
                    </div>
                    <div style="background: rgba(255,42,68,0.1); border: 2px solid var(--red); padding: 1.5vh; border-radius: 12px;">
                        <span style="color: var(--red); font-size: 1.1rem; font-weight: bold;">INCORRECT / PENALIZED</span>
                        <div style="font-size: 2.5rem; color: #fff; font-weight: 900;">${stats.wrong_count || 0}</div>
                    </div>
                    <div style="background: rgba(0,240,255,0.1); border: 2px solid var(--cyan); padding: 1.5vh; border-radius: 12px;">
                        <span style="color: var(--cyan); font-size: 1.1rem; font-weight: bold;">⚡ FASTEST SOLVE</span>
                        <div style="font-size: 1.4rem; color: #fff; font-weight: 900; margin-top: 5px;">${fastest}</div>
                    </div>
                </div>
            </div>
        `;
        if (window.soundEngine) window.soundEngine.playCorrect();
    } else if (phase === 'FINAL_60') {
        stage.innerHTML = `
            <div class="final-60-aura">
                <h1 style="color: var(--red); font-size: clamp(2.5rem, 5vw, 5rem); text-shadow: var(--red-glow);">THE FINAL 60 SECONDS</h1>
                <p style="font-size: clamp(1.4rem, 2.5vw, 2.5rem); color: #fff; font-family: var(--font-sub);" class="mt-2">TOP 5 FINALISTS: ENTER ULTIMATE MASTER CODE!</p>
                <div class="final-60-timer-digits mt-3" id="final-60-timer">60</div>
            </div>
        `;
        if (window.soundEngine) window.soundEngine.playWarning();
    } else if (phase === 'ELIMINATION' || phase === 'ELIMINATED') {
        fetch('/api/leaderboard')
        .then(res => res.json())
        .then(lb => {
            const safeTeams = lb.filter(t => t.status !== 'ELIMINATED');
            const elimTeams = lb.filter(t => t.status === 'ELIMINATED');

            stage.innerHTML = `
                <div class="proj-elimination-grid">
                    <div class="proj-elim-card proj-safe">
                        <h2 style="color: var(--green); text-shadow: var(--green-glow);">✅ SURVIVING TEAMS (${safeTeams.length})</h2>
                        <div class="proj-team-list">
                            ${safeTeams.map(t => `
                                <div class="proj-team-item safe-item">
                                    <span>Rank #${t.rank} — <strong>${t.team_name}</strong></span>
                                    <span style="color: var(--green);">${t.score} pts</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    <div class="proj-elim-card proj-danger">
                        <h2 style="color: var(--red); text-shadow: var(--red-glow);">❌ ELIMINATED TEAMS (${elimTeams.length})</h2>
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
            if (window.soundEngine) window.soundEngine.playWrong();
        });
    } else if (phase === 'WINNER') {
        fetch('/api/state')
        .then(res => res.json())
        .then(st => {
            stage.innerHTML = `
                <div class="winner-climax-box">
                    <h1 class="glitch-title">ESCAPE COMPLETE!</h1>
                    <h2 style="color: var(--gold); font-size: clamp(2rem, 4vw, 4rem); margin-top: 10px;">VICTORY UNLOCKED</h2>
                    <div class="winner-team-name">🏆 ULTIMATE CHAMPION DECLARED! 🏆</div>
                    <div class="prize-banner mt-4">FIRST PRIZE: ₹3,000 + CHAMPION TROPHY</div>
                </div>
            `;
            if (window.soundEngine) window.soundEngine.playVictory();
        });
    } else if (phase === 'LEADERBOARD') {
        fetch('/api/leaderboard')
        .then(res => res.json())
        .then(lb => {
            stage.innerHTML = `
                <div class="proj-challenge-box" style="width: 85%;">
                    <h1 style="color: var(--gold); font-size: 3rem;">LIVE LEADERBOARD</h1>
                    <table class="hud-table" style="font-size: 1.4rem;">
                        <thead>
                            <tr><th>Rank</th><th>Team</th><th>Score</th><th>Status</th></tr>
                        </thead>
                        <tbody>
                            ${lb.slice(0, 10).map(t => `
                                <tr>
                                    <td><strong>#${t.rank}</strong></td>
                                    <td>${t.team_name}</td>
                                    <td><strong style="color: var(--cyan);">${t.score} pts</strong></td>
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
