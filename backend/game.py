"""Rules and mutable state for a 3-by-3 game of Tic-Tac-Toe.

Positions use flat, row-major indices from 0 through 8. The API uses a nested
3-by-3 board; conversion between those shapes belongs at the Flask boundary.
"""

from __future__ import annotations

from collections.abc import Sequence

PLAYER_X = "X"
PLAYER_O = "O"
PLAYERS = (PLAYER_X, PLAYER_O)
EMPTY = ""

WINNING_LINES: tuple[tuple[int, int, int], ...] = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
)


class TicTacToe:
    """A game state whose board is a flat list of nine cells.

    Args:
        board: Optional row-major sequence of nine ``"X"``, ``"O"``, or
            ``EMPTY`` values. A copy is stored so the caller's sequence is
            never mutated.
        current_player: Symbol allowed to make the next move.

    ``make_move`` raises ``ValueError`` for invalid positions, symbols,
    out-of-turn moves, occupied cells, or moves after the game ends.
    ``undo_move`` raises ``ValueError`` unless ``pos`` is the most recent
    move made through this instance. Undo is a search rollback and restores
    the exact prior board and turn.
    """

    def __init__(
        self,
        board: Sequence[str] | None = None,
        current_player: str = PLAYER_X,
    ) -> None:
        if current_player not in PLAYERS:
            raise ValueError("current_player must be 'X' or 'O'")

        cells = [EMPTY] * 9 if board is None else list(board)
        if len(cells) != 9:
            raise ValueError("board must contain exactly nine cells")
        if any(cell not in (*PLAYERS, EMPTY) for cell in cells):
            raise ValueError("board cells must be 'X', 'O', or EMPTY")

        self.board: list[str] = cells
        self.current_player = current_player
        self._move_history: list[tuple[int, str, str]] = []

    @staticmethod
    def _valid_position(pos: object) -> bool:
        return isinstance(pos, int) and not isinstance(pos, bool) and 0 <= pos < 9

    def is_valid_move(self, pos: object, player: str | None = None) -> bool:
        """Return whether ``pos`` is a legal move for the current turn."""
        if not self._valid_position(pos) or self.is_game_over():
            return False
        if self.board[pos] != EMPTY:  # type: ignore[index]
            return False
        if player is not None and (player not in PLAYERS or player != self.current_player):
            return False
        return True

    def get_available_moves(self) -> list[int]:
        """Return legal row-major positions in ascending order."""
        if self.is_game_over():
            return []
        return [pos for pos, cell in enumerate(self.board) if cell == EMPTY]

    def make_move(self, pos: int, player: str | None = None) -> bool:
        """Place the current player's symbol at ``pos`` and advance the turn.

        ``player`` is optional for compatibility with callers that rely on
        ``current_player``. If supplied, it must match the current turn.
        Returns ``True`` after a successful move; invalid operations raise
        ``ValueError``.
        """
        if not self._valid_position(pos):
            raise ValueError("pos must be an integer from 0 through 8")
        symbol = self.current_player if player is None else player
        if symbol not in PLAYERS:
            raise ValueError("player must be 'X' or 'O'")
        if symbol != self.current_player:
            raise ValueError(f"it is {self.current_player}'s turn")
        if self.is_game_over():
            raise ValueError("cannot make a move after the game has ended")
        if self.board[pos] != EMPTY:
            raise ValueError(f"position {pos} is already occupied")

        previous_player = self.current_player
        self.board[pos] = symbol
        self._move_history.append((pos, symbol, previous_player))
        self.current_player = PLAYER_O if symbol == PLAYER_X else PLAYER_X
        return True

    def undo_move(self, pos: int) -> bool:
        """Undo the most recent move at ``pos`` and restore its prior turn.

        Requiring last-in-first-out undo keeps nested search branches exact.
        Returns ``True`` on success; invalid operations raise ``ValueError``.
        """
        if not self._valid_position(pos):
            raise ValueError("pos must be an integer from 0 through 8")
        if not self._move_history:
            raise ValueError("there is no move to undo")

        last_pos, symbol, previous_player = self._move_history[-1]
        if pos != last_pos or self.board[pos] != symbol:
            raise ValueError("moves must be undone in reverse order")

        self._move_history.pop()
        self.board[pos] = EMPTY
        self.current_player = previous_player
        return True

    def check_winner(self) -> str | None:
        """Return the winning symbol, or ``None`` if there is no winner."""
        for line in WINNING_LINES:
            first = self.board[line[0]]
            if first in PLAYERS and all(self.board[pos] == first for pos in line[1:]):
                return first
        return None

    def get_winning_line(self) -> tuple[int, int, int] | None:
        """Return the first winning line in ``WINNING_LINES`` order, if any."""
        for line in WINNING_LINES:
            first = self.board[line[0]]
            if first in PLAYERS and all(self.board[pos] == first for pos in line[1:]):
                return line
        return None

    def is_draw(self) -> bool:
        """Return whether all cells are filled and neither player has won."""
        return self.check_winner() is None and all(cell != EMPTY for cell in self.board)

    def is_game_over(self) -> bool:
        """Return whether the board has a winner or is a draw."""
        return self.check_winner() is not None or self.is_draw()
