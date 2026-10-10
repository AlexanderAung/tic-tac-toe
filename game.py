"""Compatibility exports for the game engine in :mod:`backend.game`."""

from backend.game import EMPTY, PLAYER_O, PLAYER_X, PLAYERS, WINNING_LINES
from backend.game import TicTacToe as _BackendTicTacToe


class TicTacToe(_BackendTicTacToe):
    """Root-level adapter preserving the original tests' occupied-move API."""

    def make_move(self, pos: int, player: str | None = None) -> bool:
        try:
            return super().make_move(pos, player)
        except ValueError:
            # The original root-module API used False for an occupied cell.
            # Keep that compatibility here; backend.game remains exception-based.
            if (
                self._valid_position(pos)
                and self.board[pos] != EMPTY
                and not self.is_game_over()
                and (player is None or player == self.current_player)
            ):
                return False
            raise


__all__ = ["EMPTY", "PLAYER_O", "PLAYER_X", "PLAYERS", "WINNING_LINES", "TicTacToe"]
