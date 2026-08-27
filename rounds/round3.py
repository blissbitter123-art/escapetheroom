from game.game_engine import GameEngine
from game.elimination import EliminationEngine
from game.round_manager import RoundManager

class Round3Controller:
    ROUND_NUMBER = 3
    START_TEAMS = 20
    CUTOFF_TEAMS = 5

    @classmethod
    def start(cls):
        """Start Round 3: The Lock & Gamble."""
        RoundManager.advance_round(3)

    @classmethod
    def execute_elimination(cls):
        """Cutoff 15 teams to produce Top 5 Finalists (20 -> 5)."""
        return EliminationEngine.execute_round_elimination(cls.ROUND_NUMBER, cls.CUTOFF_TEAMS)
