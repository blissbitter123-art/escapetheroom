from game.game_engine import GameEngine
from game.elimination import EliminationEngine
from game.round_manager import RoundManager

class Round1Controller:
    ROUND_NUMBER = 1
    START_TEAMS = 50
    CUTOFF_TEAMS = 40

    @classmethod
    def start(cls):
        """Start Round 1: The Room Wakes Up."""
        RoundManager.advance_round(1)

    @classmethod
    def execute_elimination(cls):
        """Cutoff bottom 10 teams (50 -> 40)."""
        return EliminationEngine.execute_round_elimination(cls.ROUND_NUMBER, cls.CUTOFF_TEAMS)
