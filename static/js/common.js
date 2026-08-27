/* ESCAPE THE ROOM: THE FINAL 60 - COMMON UTILITIES & SYNTH AUDIO ENGINE */

// Synthetic Web Audio API Sound Generator (No external MP3 download dependency required!)
class SoundEngine {
    constructor() {
        this.ctx = null;
        this.enabled = true;
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

    playBeep(freq = 880, type = 'sine', duration = 0.1) {
        if (!this.enabled) return;
        this.init();
        if (!this.ctx) return;

        try {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = type;
            osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
            gain.gain.setValueAtTime(0.2, this.ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + duration);

            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start();
            osc.stop(this.ctx.currentTime + duration);
        } catch (e) {
            console.error("Audio error:", e);
        }
    }

    playTick() { this.playBeep(1000, 'sine', 0.05); }
    playWarning() { this.playBeep(440, 'sawtooth', 0.3); }
    playCorrect() {
        this.playBeep(523.25, 'triangle', 0.1);
        setTimeout(() => this.playBeep(659.25, 'triangle', 0.1), 100);
        setTimeout(() => this.playBeep(783.99, 'triangle', 0.2), 200);
    }
    playWrong() {
        this.playBeep(220, 'sawtooth', 0.2);
        setTimeout(() => this.playBeep(180, 'sawtooth', 0.3), 150);
    }
    playVictory() {
        const notes = [523.25, 659.25, 783.99, 1046.50];
        notes.forEach((freq, idx) => {
            setTimeout(() => this.playBeep(freq, 'square', 0.3), idx * 150);
        });
    }
}

window.soundEngine = new SoundEngine();

// Format seconds into MM:SS
function formatTime(seconds) {
    if (seconds === null || seconds === undefined || seconds < 0) return "00:00";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// User gesture unlock for audio
document.addEventListener('click', () => {
    if (window.soundEngine) window.soundEngine.init();
}, { once: true });
