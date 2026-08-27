# ESCAPE THE ROOM: "THE FINAL 60"

A live, high-energy, interactive local-network game-show system designed to conduct a physical escape room competition with 50 teams, 3 elimination rounds, and 1 final winner.

## Quick Start (Windows)
1. Connect the Host Laptop to the local event Wi-Fi/LAN router.
2. Double-click `run_windows.bat` to launch the server.
3. Access the interfaces:
   - **Host Control Room**: `http://127.0.0.1:5000/control`
   - **Projector Display**: `http://127.0.0.1:5000/projector`
   - **Team Leader Phone**: `http://<YOUR_HOST_LAN_IP>:5000/team/login`

## Progression & Cutoffs
- **Round 1**: 50 → 40 Teams (The Room Wakes Up)
- **Round 2**: 40 → 20 Teams (The Host Is Lying)
- **Round 3**: 20 → Top 5 Finalists (The Lock & Gamble)
- **Final 60**: Top 5 → 1 Winner (60-Second Climax)

## Technology Stack
- **Backend**: Python 3, Flask, SQLite
- **Frontend**: Cyber HUD HTML5, CSS3, Vanilla JS
- **Audio**: Built-in Synthetic Web Audio Engine
