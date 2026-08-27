import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import init_db, query_db
from game.game_engine import GameEngine

def run_event_rehearsal_simulation():
    print("=" * 65)
    print("      RUNNING FULL 50-TEAM REHEARSAL EVENT SIMULATION      ")
    print("=" * 65)

    init_db()
    winner_team = GameEngine.run_demo_simulation()

    print("\n[SUCCESS] Rehearsal simulation finished successfully!")
    print(f" Champion Winner Team: Team {winner_team['team_number']} ({winner_team['team_name']})")
    print(f" Final Score: {winner_team['score']} pts")

    print("\nEvent Log Summary:")
    logs = query_db("SELECT * FROM event_logs ORDER BY created_at ASC LIMIT 20")
    for l in logs:
        print(f" - [{l['created_at']}] {l['event_type']}: {l['description']}")

    print("=" * 65)

if __name__ == '__main__':
    run_event_rehearsal_simulation()
