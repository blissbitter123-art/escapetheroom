/* TEAM MOBILE INTERFACE CONTROLLER JS */

let teamTimer = new ClientTimer('team-timer');
let currentChallengeStart = null;
let activeChallengeId = null;
let lastPhase = null;
let lastSubId = null;
let lastWagerSignature = null;
let lastPurchasedSignature = null;

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

        // Re-render team content area if phase, submission, wager, or hints changed
        const currentSubId = state.team_submission ? state.team_submission.id : null;
        const wagerType = state.team_wager ? state.team_wager.wager_type : (state.team && state.team.round3_wager_type ? state.team.round3_wager_type : '');
        const wagerSig = state.team_wager ? (state.team_wager.id + ':' + wagerType) : (wagerType ? ('team:' + wagerType) : '');
        const purchasedSig = (state.purchased_clues || []).map(c => c.clue_id || c.id).join(',');

        if (state.current_phase !== lastPhase || currentSubId !== lastSubId || wagerSig !== lastWagerSignature || purchasedSig !== lastPurchasedSignature) {
            renderTeamContent(state);
            lastPhase = state.current_phase;
            lastSubId = currentSubId;
            lastWagerSignature = wagerSig;
            lastPurchasedSignature = purchasedSig;
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
            // Round 3 Gamble flow: 1) choose wager  2) question appears with wager badge  3) score adjusted on answer
            let wagerData = {};
            try { wagerData = ch.display_data_json ? JSON.parse(ch.display_data_json) : {}; } catch(e) {}
            
            let teamWager = state.team_wager;
            if (!teamWager && state.team && state.team.round3_wager_type) {
                const wt = state.team.round3_wager_type;
                teamWager = {
                    wager_type: wt,
                    multiplier: (wt === 'RISK' ? 2 : (wt === 'ALL_IN' ? 3 : 1)),
                    penalty: (wt === 'RISK' ? 10 : (wt === 'ALL_IN' ? 25 : 0))
                };
            }

            if (!teamWager) {
                inputControls = `
                    <div class="wager-selection-screen">
                        <div class="wager-modal-header">
                            <div class="wager-eyebrow">⚖️ ROUND 3 HIGH-STAKES GAMBLE</div>
                            <h3 class="wager-title">SELECT YOUR RISK LEVEL</h3>
                            <p class="wager-subtitle">Lock in your team's wager choice before revealing the question:</p>
                        </div>
                        <div class="wager-options-grid">
                            <div class="wager-card wager-card-safe">
                                <div class="wager-card-icon">🛡️</div>
                                <h4>SAFE</h4>
                                <div class="wager-badge-payout text-green">+20 pts (1x)</div>
                                <div class="wager-penalty-payout text-muted">0 Penalty</div>
                                <p class="wager-card-desc">Low reward, zero loss penalty.</p>
                                <button onclick="submitWager('SAFE')" class="wager-btn safe-wager">LOCK SAFE 🛡️</button>
                            </div>
                            <div class="wager-card wager-card-risk">
                                <div class="wager-card-icon">⚡</div>
                                <h4>RISK</h4>
                                <div class="wager-badge-payout text-warning">+40 pts (2x)</div>
                                <div class="wager-penalty-payout text-danger">-10 Penalty</div>
                                <p class="wager-card-desc">High reward, medium penalty.</p>
                                <button onclick="submitWager('RISK')" class="wager-btn risk-wager">LOCK RISK ⚡</button>
                            </div>
                            <div class="wager-card wager-card-allin">
                                <div class="wager-card-icon">💀</div>
                                <h4>ALL IN</h4>
                                <div class="wager-badge-payout text-danger">+60 pts (3x)</div>
                                <div class="wager-penalty-payout text-danger">-25 Penalty</div>
                                <p class="wager-card-desc">High reward, severe penalty!</p>
                                <button onclick="submitWager('ALL_IN')" class="wager-btn allin-wager">LOCK ALL IN 💀</button>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                const wagerLabel = teamWager.wager_type.replace('_', ' ');
                const qText = wagerData.question || ch.description;
                let questionOptions = wagerData.question_options;
                if ((!questionOptions || !questionOptions.length) && ch.options_json && ch.options_json !== '[]') {
                    try { questionOptions = JSON.parse(ch.options_json); } catch(err) { questionOptions = null; }
                }
                const answerControls = (questionOptions && questionOptions.length)
                    ? `<div class="options-grid">
                        ${questionOptions.map(opt => `<button onclick="submitTeamAnswer('${opt}')" class="btn-cyan btn-option">${opt}</button>`).join('')}
                       </div>`
                    : renderTextInputBox();
                inputControls = `
                    <div class="current-wager-status-badge wager-tier-${teamWager.wager_type.toLowerCase()}">
                        <span class="status-indicator-dot"></span>
                        <span class="status-text">Current Wager: <strong>${wagerLabel}</strong></span>
                        <span class="status-detail">(${teamWager.multiplier}x points / -${teamWager.penalty} if wrong)</span>
                    </div>
                    <div class="challenge-question-box"><span class="hint-label">THE QUESTION</span><p>${qText}</p></div>
                    ${answerControls}
                `;
            }
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

        // Include hint section for Round 3 or challenges with clues (when not choosing wager)
        const isGambleSelecting = (ch.challenge_type === 'GAMBLE_WAGER' && !state.team_wager && !(state.team && state.team.round3_wager_type));
        if (!isGambleSelecting && (state.current_round === 3 || (state.challenge_clues && state.challenge_clues.length > 0) || (state.purchased_clues && state.purchased_clues.length > 0))) {
            inputControls += renderHintSection(state);
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

/* ─── ROUND 3 GAMBLE: LOCK THE WAGER FIRST ───────────────────── */
function submitWager(wagerType) {
    if (!activeChallengeId) {
        alert("No active challenge to wager on.");
        return;
    }
    if (!confirm(`Lock in ${wagerType.replace('_', '-')} for this gamble? Your stake cannot be changed.`)) return;

    fetch('/team/wager', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ challenge_id: activeChallengeId, wager_type: wagerType })
    })
    .then(res => res.json())
    .then(data => {
        if (!data.success) {
            alert('Wager lock failed: ' + (data.error || 'Unknown Error'));
            return;
        }
        pollTeamState(); // re-renders the question step
    })
    .catch(err => console.error('Wager lock request failed:', err));
}

/* ─── ROUND 3 & GENERAL: HINT PURCHASE & DISPLAY ─────────────── */
function renderHintSection(state) {
    const clues = state.challenge_clues || [];
    const purchased = state.purchased_clues || [];
    const purchasedHints = state.purchased_hints || [];

    const unpurchasedClues = clues.filter(c => !c.is_purchased);
    const hasUnpurchased = unpurchasedClues.length > 0 || clues.length === 0;

    let hintsHtml = '';
    if (purchased.length > 0) {
        hintsHtml = purchased.map((p, idx) => `
            <div class="revealed-hint-card">
                <span class="hint-badge">💡 HINT #${idx + 1}</span>
                <p class="hint-text">${p.clue_text}</p>
            </div>
        `).join('');
    } else if (purchasedHints.length > 0) {
        hintsHtml = purchasedHints.map((txt, idx) => `
            <div class="revealed-hint-card">
                <span class="hint-badge">💡 HINT #${idx + 1}</span>
                <p class="hint-text">${txt}</p>
            </div>
        `).join('');
    }

    const nextCost = (unpurchasedClues.length > 0) ? unpurchasedClues[0].cost_points : 10;
    const teamScore = (state.team && state.team.score !== undefined) ? state.team.score : 0;
    const canAfford = teamScore >= nextCost;

    let buyButton = '';
    if (!hasUnpurchased) {
        buyButton = `<span class="text-muted hint-all-unlocked" id="hint-status-text">All Hints Unlocked</span>`;
    } else if (!canAfford) {
        buyButton = `<button type="button" onclick="buyHint()" class="btn-sm btn-muted btn-buy-hint disabled-btn" id="buy-hint-btn" title="Need ${nextCost} pts to unlock">⚠️ INSUFFICIENT PTS (${teamScore}/${nextCost})</button>`;
    } else {
        buyButton = `<button type="button" onclick="buyHint()" class="btn-sm btn-gold btn-buy-hint" id="buy-hint-btn">💡 BUY HINT (-${nextCost} PTS)</button>`;
    }

    return `
        <div class="hint-section-box mt-4">
            <div class="hint-header-row">
                <span class="hint-section-title">💡 INTEL & HINTS</span>
                ${buyButton}
            </div>
            <div class="hint-container" id="hint-container">
                ${hintsHtml}
            </div>
        </div>
    `;
}

function buyHint(clueId) {
    if (!activeChallengeId) {
        alert("No active challenge to buy hints for.");
        return;
    }

    const sEl = document.getElementById('team-score');
    const currentScore = sEl ? parseInt(sEl.textContent.trim(), 10) : 0;
    if (!isNaN(currentScore) && currentScore < 10) {
        alert(`Insufficient points! You have ${currentScore} pts. You cannot buy a hint if your score would go negative.`);
        return;
    }

    if (!confirm("Purchase a hint? Points will be deducted from your score.")) return;

    fetch('/api/buy_hint', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ challenge_id: activeChallengeId, clue_id: clueId || null })
    })
    .then(res => res.json())
    .then(data => {
        if (!data.success) {
            alert('Hint purchase error: ' + (data.error || 'Could not purchase hint'));
            return;
        }

        // Dynamically append and display the purchased hint text inside dedicated <div class="hint-container">
        let container = document.getElementById('hint-container');
        if (!container) {
            container = document.querySelector('.hint-container');
        }

        if (container && data.hint) {
            const existingTexts = Array.from(container.querySelectorAll('.hint-text')).map(el => el.textContent.trim());
            if (!existingTexts.includes(data.hint.trim())) {
                const hintNum = container.querySelectorAll('.revealed-hint-card').length + 1;
                const hintCard = document.createElement('div');
                hintCard.className = 'revealed-hint-card hint-card-new';
                hintCard.innerHTML = `
                    <span class="hint-badge">💡 HINT #${hintNum}</span>
                    <p class="hint-text">${data.hint}</p>
                `;
                container.appendChild(hintCard);
            }
        }

        // Update score display immediately
        if (data.remaining_score !== undefined) {
            const sEl = document.getElementById('team-score');
            if (sEl) sEl.textContent = data.remaining_score;
        }

        // Alert popup notification
        alert(data.message || 'Hint unlocked! Check your hints below.');

        // Re-sync team state
        pollTeamState();
    })
    .catch(err => {
        console.error('Hint purchase request failed:', err);
        alert('Network error while purchasing hint.');
    });
}

// Start 1-second polling loop
setInterval(pollTeamState, 1000);
pollTeamState();
