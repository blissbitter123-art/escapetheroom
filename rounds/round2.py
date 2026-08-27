from game.game_engine import GameEngine
from game.elimination import EliminationEngine
from game.round_manager import RoundManager

class Round2Controller:
    ROUND_NUMBER = 2
    START_TEAMS = 40
    CUTOFF_TEAMS = 20

    @classmethod
    def start(cls):
        """Start Round 2: The Host Is Lying."""
        RoundManager.advance_round(2)

    @classmethod
    def execute_elimination(cls):
        """Cutoff bottom 20 teams (40 -> 20)."""
        return EliminationEngine.execute_round_elimination(cls.ROUND_NUMBER, cls.CUTOFF_TEAMS)
