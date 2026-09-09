/* HOST CONTROL PANEL JS */

let hostTimer = new ClientTimer('kpi-timer');

function hostAction(action, payload = {}) {
    payload.action = action;
    fetch('/api/host/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if (!data.success) {
            alert('Host Action Failed: ' + (data.error || 'Unknown Error'));
        } else {
            pollHostState();
        }
    })
    .catch(err => console.error('Error executing host action:', err));
}

function pollHostState() {
    fetch('/api/state')
    .then(res => res.json())
    .then(state => {
        // Update KPIs
        const rEl = document.getElementById('kpi-round');
        if (rEl) rEl.textContent = `Round ${state.current_round}`;
        
        const rtEl = document.getElementById('kpi-round-title');
        if (rtEl) rtEl.textContent = state.round_title;

        const cEl = document.getElementById('kpi-challenge');
        if (cEl) cEl.textContent = state.active_challenge ? state.active_challenge.title : 'NO ACTIVE CHALLENGE';

        const pEl = document.getElementById('kpi-phase');
        if (pEl) pEl.textContent = `Phase: ${state.current_phase}`;

        const aEl = document.getElementById('kpi-active-count');
        if (aEl) aEl.textContent = state.active_teams_count;

        const eEl = document.getElementById('kpi-eliminated-count');
        if (eEl) eEl.textContent = state.eliminated_teams_count;

        // Update timer
        if (state.timer) {
            hostTimer.update(state.timer.remaining, state.timer.is_running, state.timer.is_paused);
        }
    });

    // Poll logs
    fetch('/api/logs')
    .then(res => res.json())
    .then(logs => {
        const feed = document.getElementById('log-feed');
        if (!feed) return;
        feed.innerHTML = logs.map(l => `
            <div class="log-item">
                <span class="log-time">[${l.created_at.split(' ')[1] || l.created_at}]</span>
                <strong>${l.event_type}</strong>: ${l.description}
            </div>
        `).join('');
    });
}

// Start 1-second polling loop
setInterval(pollHostState, 1000);
pollHostState();

function generateTeams() {
    let count = document.getElementById('teamCountInput').value;
    if (confirm(`WARNING: This will delete ALL existing teams, scores, and submissions, and generate ${count} new teams with random PINs. Are you absolutely sure?`)) {
        hostAction('generate_teams', { count: parseInt(count) });
        setTimeout(() => location.reload(), 500); // reload to see new teams
    }
}

function updateTeamName(teamId) {
    let nameInput = document.getElementById(`teamName_${teamId}`);
    let newName = nameInput.value.trim();
    if (newName) {
        hostAction('update_team_name', { team_id: teamId, team_name: newName });
        alert('Team name updated!');
    }
}

/* ─── CHALLENGE MODAL & CRUD FUNCTIONS ─── */
function openChallengeModal(data = null) {
    const modal = document.getElementById('challengeModal');
    if (!modal) return;
    const titleEl = document.getElementById('modalTitle');
    const form = document.getElementById('challengeForm');
    
    if (data) {
        titleEl.textContent = 'EDIT CHALLENGE: ' + data.challenge_key;
        document.getElementById('ch_id').value = data.id || '';
        document.getElementById('ch_key').value = data.challenge_key || '';
        document.getElementById('ch_round').value = data.round_id || 1;
        document.getElementById('ch_title').value = data.title || '';
        document.getElementById('ch_type').value = data.challenge_type || 'SPEED_TEST';
        document.getElementById('ch_desc').value = data.description || '';
        document.getElementById('ch_duration').value = data.duration_sec || 60;
        const mediaDurEl = document.getElementById('ch_media_duration');
        if (mediaDurEl) mediaDurEl.value = data.media_visibility_duration_sec || 15;
        document.getElementById('ch_action').value = data.expected_action || 'SUBMIT_ANSWER';
        document.getElementById('ch_answer').value = data.correct_answer || '';
        document.getElementById('ch_diff').value = data.difficulty || 'EASY';
        document.getElementById('ch_points').value = data.base_points || 10;
        document.getElementById('ch_bonus').value = data.speed_bonus_points || 0;
        document.getElementById('ch_penalty').value = data.penalty_points || 0;
        document.getElementById('ch_order').value = data.order_index || 1;
        document.getElementById('ch_display_json').value = data.display_data_json || '';
        document.getElementById('ch_options_json').value = data.options_json || '';
        renderClueRows(data.clues || []);
    } else {
        titleEl.textContent = 'CREATE NEW CHALLENGE';
        form.reset();
        document.getElementById('ch_id').value = '';
        renderClueRows([]);
    }
    modal.style.display = 'flex';
}

/* ─── CLUES / HINTS EDITOR (Challenges edit screen) ─────────── */
function renderClueRows(clues) {
    const container = document.getElementById('clueRows');
    if (!container) return;
    container.innerHTML = '';
    if (!clues || !clues.length) {
        addClueRow();
        return;
    }
    clues.forEach(c => addClueRow(c.clue_text || '', c.cost_points || 10));
}

function addClueRow(clueText = '', cost = 10) {
    const container = document.getElementById('clueRows');
    if (!container) return;
    const safeText = String(clueText).replace(/"/g, '&quot;').replace(/</g, '&lt;');
    container.insertAdjacentHTML('beforeend', `
        <div class="clue-row" style="display: flex; gap: 8px; align-items: center; margin-bottom: 6px;">
            <input type="text" class="input-hud" style="flex: 1;" placeholder="Hint text..." value="${safeText}">
            <input type="number" class="input-hud-sm" style="width: 80px;" min="0" value="${cost}" title="Cost in points (informational)">
            <button type="button" onclick="removeClueRow(this)" class="btn-sm btn-danger" title="Remove hint">✕</button>
        </div>
    `);
}

function removeClueRow(btn) {
    const row = btn.closest ? (btn.closest('.clue-row') || btn.parentElement) : btn.parentElement;
    if (row) row.remove();
}

function collectClues() {
    const container = document.getElementById('clueRows');
    if (!container) return [];
    return Array.from(container.querySelectorAll('.clue-row'))
        .map(row => {
            const inputs = row.querySelectorAll('input');
            const clue_text = inputs[0].value.trim();
            const cost_points = parseInt(inputs[1].value, 10);
            return { clue_text, cost_points: isNaN(cost_points) ? 0 : cost_points };
        })
        .filter(c => c.clue_text.length > 0);
}

function closeChallengeModal() {
    const modal = document.getElementById('challengeModal');
    if (modal) modal.style.display = 'none';
}

function editChallenge(chId) {
    fetch('/api/host/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'get_challenge', challenge_id: chId })
    })
    .then(res => res.json())
    .then(res => {
        if (res.success) {
            openChallengeModal(res.challenge);
        } else {
            alert('Failed to load challenge details: ' + (res.error || 'Unknown error'));
        }
    })
    .catch(err => console.error('Error fetching challenge:', err));
}

function deleteChallenge(chId, title) {
    if (confirm(`Are you sure you want to delete challenge "${title}"? This cannot be undone.`)) {
        fetch('/api/host/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'delete_challenge', challenge_id: chId })
        })
        .then(res => res.json())
        .then(res => {
            if (res.success) {
                location.reload();
            } else {
                alert('Delete failed: ' + (res.error || 'Unknown error'));
            }
        });
    }
}

function saveChallengeForm(event) {
    event.preventDefault();
    const displayJson = document.getElementById('ch_display_json').value.trim();
    const optionsJson = document.getElementById('ch_options_json').value.trim();

    if (displayJson) {
        try { JSON.parse(displayJson); } catch (e) {
            alert('Invalid JSON in Display Data: ' + e.message);
            return;
        }
    }
    if (optionsJson) {
        try { JSON.parse(optionsJson); } catch (e) {
            alert('Invalid JSON in Options: ' + e.message);
            return;
        }
    }

    const payload = {
        action: 'save_challenge',
        challenge: {
            id: document.getElementById('ch_id').value ? parseInt(document.getElementById('ch_id').value) : null,
            challenge_key: document.getElementById('ch_key').value.trim(),
            round_id: parseInt(document.getElementById('ch_round').value),
            title: document.getElementById('ch_title').value.trim(),
            challenge_type: document.getElementById('ch_type').value.trim(),
            description: document.getElementById('ch_desc').value.trim(),
            duration_sec: parseInt(document.getElementById('ch_duration').value),
            media_visibility_duration_sec: document.getElementById('ch_media_duration') ? parseInt(document.getElementById('ch_media_duration').value) : 15,
            expected_action: document.getElementById('ch_action').value,
            correct_answer: document.getElementById('ch_answer').value.trim(),
            difficulty: document.getElementById('ch_diff').value,
            base_points: parseInt(document.getElementById('ch_points').value),
            speed_bonus_points: parseInt(document.getElementById('ch_bonus').value),
            penalty_points: parseInt(document.getElementById('ch_penalty').value),
            order_index: parseInt(document.getElementById('ch_order').value),
            display_data_json: displayJson,
            options_json: optionsJson,
            clues: collectClues()
        }
    };

    fetch('/api/host/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(res => {
        if (res.success) {
            closeChallengeModal();
            location.reload();
        } else {
            alert('Save Challenge Failed: ' + (res.error || 'Unknown Error'));
        }
    })
    .catch(err => alert('Network error while saving challenge: ' + err));
}

function launchChallengeWithDurations(challengeId, challengeKey) {
    const qInput = document.getElementById(`dash_q_dur_${challengeId}`) || document.getElementById(`ch_q_dur_${challengeId}`);
    const mInput = document.getElementById(`dash_m_dur_${challengeId}`) || document.getElementById(`ch_m_dur_${challengeId}`);

    const qDur = qInput ? parseInt(qInput.value, 10) : 45;
    const mDur = mInput ? parseInt(mInput.value, 10) : 15;

    const payload = {
        question_id: challengeKey || `ch_${challengeId}`,
        challenge_id: challengeId,
        duration: isNaN(qDur) ? 45 : qDur,
        media_visibility_duration: isNaN(mDur) ? 15 : mDur
    };

    hostAction('start_challenge', payload);
}
