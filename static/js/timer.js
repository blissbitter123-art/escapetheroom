/* TIMER MANAGER SCRIPT */

class ClientTimer {
    constructor(elementId) {
        this.elementId = elementId;
        this.remaining = 0;
        this.isRunning = false;
        this.interval = null;
    }

    update(remainingSec, isRunning, isPaused) {
        this.remaining = Math.max(0, remainingSec);
        this.isRunning = isRunning;
        this.render();

        if (this.interval) clearInterval(this.interval);

        if (this.isRunning && !isPaused) {
            this.interval = setInterval(() => {
                if (this.remaining > 0) {
                    this.remaining--;
                    this.render();
                } else {
                    clearInterval(this.interval);
                }
            }, 1000);
        }
    }

    render() {
        const el = document.getElementById(this.elementId);
        if (el) {
            el.textContent = formatTime(this.remaining);
            if (this.remaining <= 10 && this.remaining > 0 && this.isRunning) {
                el.classList.add('text-danger');
                if (window.soundEngine) window.soundEngine.playTick();
            } else {
                el.classList.remove('text-danger');
            }
        }
    }
}

window.ClientTimer = ClientTimer;
