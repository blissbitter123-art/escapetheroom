/* ═══════════════════════════════════════════════════════════════
   ESCAPE THE ROOM: THE FINAL 60 — HORROR SOUND ENGINE
   Procedurally generated horror sounds via Web Audio API.
   No external files required.
   ═══════════════════════════════════════════════════════════════ */

class SoundEngine {
    constructor() {
        this.ctx = null;
        this.enabled = true;
        this._heartbeatInterval = null;
    }

    init() {
        if (!this.ctx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                this.ctx = new AudioContext();
            }
        }
        if (this.ctx && this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
    }

    // ─── Core oscillator builder ───────────────────────────────
    _osc(freq, type, startTime, duration, gainVal = 0.3) {
        if (!this.enabled || !this.ctx) return null;
        const osc  = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = type;
        osc.frequency.setValueAtTime(freq, startTime);
        gain.gain.setValueAtTime(gainVal, startTime);
        gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(startTime);
        osc.stop(startTime + duration);
        return { osc, gain };
    }

    // ─── Noise burst ───────────────────────────────────────────
    _noise(startTime, duration, gainVal = 0.15) {
        if (!this.enabled || !this.ctx) return;
        const bufferSize = this.ctx.sampleRate * duration;
        const buffer     = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
        const data       = buffer.getChannelData(0);
        for (let i = 0; i < bufferSize; i++) data[i] = Math.random() * 2 - 1;

        const source = this.ctx.createBufferSource();
        source.buffer = buffer;

        const filter = this.ctx.createBiquadFilter();
        filter.type  = 'bandpass';
        filter.frequency.value = 800;
        filter.Q.value = 0.5;

        const gain = this.ctx.createGain();
        gain.gain.setValueAtTime(gainVal, startTime);
        gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);

        source.connect(filter);
        filter.connect(gain);
        gain.connect(this.ctx.destination);
        source.start(startTime);
    }

    // ─── HEARTBEAT THUD ───────────────────────────────────────
    // Deep bass kick — the heart that beats before death
    _heartbeatThud(t = 0) {
        if (!this.enabled || !this.ctx) return;
        const now = this.ctx.currentTime + t;

        // Low thud — first beat
        const osc1 = this.ctx.createOscillator();
        const g1   = this.ctx.createGain();
        osc1.frequency.setValueAtTime(80, now);
        osc1.frequency.exponentialRampToValueAtTime(40, now + 0.12);
        g1.gain.setValueAtTime(0.5, now);
        g1.gain.exponentialRampToValueAtTime(0.001, now + 0.18);
        osc1.connect(g1); g1.connect(this.ctx.destination);
        osc1.start(now); osc1.stop(now + 0.2);

        // Second beat (the DUB)
        const osc2 = this.ctx.createOscillator();
        const g2   = this.ctx.createGain();
        const t2   = now + 0.28;
        osc2.frequency.setValueAtTime(70, t2);
        osc2.frequency.exponentialRampToValueAtTime(35, t2 + 0.1);
        g2.gain.setValueAtTime(0.4, t2);
        g2.gain.exponentialRampToValueAtTime(0.001, t2 + 0.15);
        osc2.connect(g2); g2.connect(this.ctx.destination);
        osc2.start(t2); osc2.stop(t2 + 0.18);
    }

    // ─── TICK (countdown beep) ────────────────────────────────
    playTick() {
        this.init();
        if (!this.ctx) return;
        this._osc(220, 'sawtooth', this.ctx.currentTime, 0.08, 0.15);
    }

    // ─── WARNING / TENSION STING ──────────────────────────────
    // Dissonant descending minor interval
    playWarning() {
        this.init();
        if (!this.ctx) return;
        const now = this.ctx.currentTime;
        this._osc(440, 'sawtooth',  now,       0.35, 0.2);
        this._osc(370, 'sawtooth',  now + 0.1, 0.4,  0.15);
        this._osc(311, 'triangle',  now + 0.2, 0.5,  0.1);
        this._noise(now, 0.3, 0.05);
    }

    // ─── CORRECT — Eerie minor chime ──────────────────────────
    playCorrect() {
        this.init();
        if (!this.ctx) return;
        const now  = this.ctx.currentTime;
        const notes = [220, 261.63, 329.63]; // minor arpeggio
        notes.forEach((freq, i) => {
            this._osc(freq, 'triangle', now + i * 0.12, 0.5, 0.12);
        });
    }

    // ─── WRONG — Blood-curdling screech ───────────────────────
    playWrong() {
        this.init();
        if (!this.ctx) return;
        const now = this.ctx.currentTime;
        // Descending screech
        const osc  = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(800, now);
        osc.frequency.exponentialRampToValueAtTime(60, now + 0.6);
        gain.gain.setValueAtTime(0.25, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.65);
        osc.connect(gain); gain.connect(this.ctx.destination);
        osc.start(now); osc.stop(now + 0.7);
        // Noise burst on top
        this._noise(now, 0.25, 0.12);
    }

    // ─── VICTORY — Ominous minor organ ────────────────────────
    playVictory() {
        this.init();
        if (!this.ctx) return;
        const now = this.ctx.currentTime;
        // Dm chord — dark triumph
        const chord = [146.83, 174.61, 220, 293.66];
        chord.forEach((freq, i) => {
            this._osc(freq, 'square', now + i * 0.18, 1.5, 0.08);
        });
        setTimeout(() => {
            const now2 = this.ctx.currentTime;
            const chord2 = [130.81, 155.56, 196, 261.63];
            chord2.forEach((freq, i) => {
                this._osc(freq, 'square', now2 + i * 0.15, 2, 0.08);
            });
        }, 900);
    }

    // ─── ELIMINATION — Jump-scare bass hit ────────────────────
    playElimination() {
        this.init();
        if (!this.ctx) return;
        const now = this.ctx.currentTime;

        // BOOM — massive sub-bass hit
        const boom = this.ctx.createOscillator();
        const bGain = this.ctx.createGain();
        boom.type = 'sine';
        boom.frequency.setValueAtTime(55, now);
        boom.frequency.exponentialRampToValueAtTime(20, now + 0.5);
        bGain.gain.setValueAtTime(0.8, now);
        bGain.gain.exponentialRampToValueAtTime(0.001, now + 0.6);
        boom.connect(bGain); bGain.connect(this.ctx.destination);
        boom.start(now); boom.stop(now + 0.65);

        // Horror string stab
        const stab  = this.ctx.createOscillator();
        const sGain = this.ctx.createGain();
        stab.type = 'sawtooth';
        stab.frequency.setValueAtTime(523.25, now + 0.05);
        stab.frequency.exponentialRampToValueAtTime(130, now + 0.4);
        sGain.gain.setValueAtTime(0.25, now + 0.05);
        sGain.gain.exponentialRampToValueAtTime(0.001, now + 0.45);
        stab.connect(sGain); sGain.connect(this.ctx.destination);
        stab.start(now + 0.05); stab.stop(now + 0.5);

        // White noise burst
        this._noise(now, 0.2, 0.15);
    }

    // ─── HEARTBEAT LOOP (for Final 60) ────────────────────────
    startHeartbeat() {
        this.init();
        if (this._heartbeatInterval) return; // already running
        this._heartbeatThud(0);
        let beat = 0;
        this._heartbeatInterval = setInterval(() => {
            beat++;
            // Speed up heartbeat as count reaches 0
            this._heartbeatThud(0);
        }, 900);
    }

    stopHeartbeat() {
        if (this._heartbeatInterval) {
            clearInterval(this._heartbeatInterval);
            this._heartbeatInterval = null;
        }
    }
}

window.soundEngine = new SoundEngine();

// ─── Utility: format seconds ──────────────────────────────────
function formatTime(seconds) {
    if (seconds === null || seconds === undefined || seconds < 0) return "00:00";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// ─── User gesture unlock for audio ───────────────────────────
document.addEventListener('click', () => {
    if (window.soundEngine) window.soundEngine.init();
}, { once: true });
