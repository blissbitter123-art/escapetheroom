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
