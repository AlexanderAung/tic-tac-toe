"""AI agents for :mod:`backend.game`.

Agents choose a flat board index with ``get_move(game)``. They do not mutate
the supplied game; Minimax temporarily makes and undoes moves during search.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence

from .game import PLAYER_O, PLAYER_X, PLAYERS, TicTacToe


def _validate_agent_turn(game: TicTacToe, player: str) -> list[int]:
    if game.is_game_over():
        raise ValueError("cannot select a move for a finished game")
    if game.current_player != player:
        raise ValueError(f"it is {game.current_player}'s turn, not {player}'s")
    moves = game.get_available_moves()
    if not moves:
        raise ValueError("there are no legal moves")
    return moves


class RandomAgent:
    """Choose uniformly from legal moves using an injectable random source."""

    def __init__(self, player: str, rng: random.Random | None = None) -> None:
        if player not in PLAYERS:
            raise ValueError("player must be 'X' or 'O'")
        self.player = player
        self.rng = rng if rng is not None else random.Random()

    def get_move(self, game: TicTacToe) -> int:
        """Return a uniformly sampled legal move; raise on a terminal game."""
        return self.rng.choice(_validate_agent_turn(game, self.player))


class HeuristicAgent:
    """Apply the priority: win, block, center, corners, then edges.

    Ties within a priority are chosen with the injectable random source. To
    detect immediate wins and blocks, the agent probes independent game-state
    copies, leaving the caller's board unchanged.
    """

    CORNERS = (0, 2, 6, 8)
    EDGES = (1, 3, 5, 7)

    def __init__(self, player: str, rng: random.Random | None = None) -> None:
        if player not in PLAYERS:
            raise ValueError("player must be 'X' or 'O'")
        self.player = player
        self.rng = rng if rng is not None else random.Random()

    def _winning_moves(self, game: TicTacToe, symbol: str) -> list[int]:
        probe = TicTacToe(game.board, current_player=symbol)
        winning_moves: list[int] = []
        for move in probe.get_available_moves():
            probe.make_move(move, symbol)
            if probe.check_winner() == symbol:
                winning_moves.append(move)
            probe.undo_move(move)
        return winning_moves

    def _choose(self, moves: Sequence[int]) -> int:
        return self.rng.choice(list(moves))

    def get_move(self, game: TicTacToe) -> int:
        """Return a legal move according to the documented priority order."""
        legal_moves = _validate_agent_turn(game, self.player)

        immediate_wins = self._winning_moves(game, self.player)
        if immediate_wins:
            return self._choose(immediate_wins)

        opponent = PLAYER_O if self.player == PLAYER_X else PLAYER_X
        opponent_threats = self._winning_moves(game, opponent)
        blocking_moves = [move for move in legal_moves if move in opponent_threats]
        if blocking_moves:
            return self._choose(blocking_moves)

        if 4 in legal_moves:
            return 4
        available_corners = [move for move in self.CORNERS if move in legal_moves]
        if available_corners:
            return self._choose(available_corners)
        available_edges = [move for move in self.EDGES if move in legal_moves]
        if available_edges:
            return self._choose(available_edges)
        # Every non-terminal 3x3 board has been exhausted by the priorities.
        raise ValueError("there are no legal moves")


class MinimaxAgent:
    """Unbeatable minimax search with optional alpha-beta pruning.

    ``nodes_visited`` counts recursive search calls (including terminal
    leaves), excluding the root move-selection wrapper. ``candidate_scores``
    maps every legal root position to its exact minimax value from this
    agent's perspective. ``alpha_beta_cutoffs`` counts internal nodes where
    the alpha-beta bounds ended exploration early. All statistics reset on
    each call to ``get_move``.
    """

    def __init__(self, player: str, use_alpha_beta: bool = True) -> None:
        if player not in PLAYERS:
            raise ValueError("player must be 'X' or 'O'")
        self.player = player
        self.use_alpha_beta = use_alpha_beta
        self.nodes_visited = 0
        self.alpha_beta_cutoffs = 0
        self.candidate_scores: dict[int, int] = {}

    @property
    def root_scores(self) -> dict[int, int]:
        """Alias for candidate scores, useful to callers visualizing the root."""
        return dict(self.candidate_scores)

    def get_move(self, game: TicTacToe) -> int:
        """Return the best legal root move, breaking ties by lowest index."""
        self.nodes_visited = 0
        self.alpha_beta_cutoffs = 0
        self.candidate_scores = {}
        legal_moves = _validate_agent_turn(game, self.player)

        # Each root branch uses a full window so its reported score is exact.
        for move in legal_moves:
            game.make_move(move, self.player)
            try:
                self.candidate_scores[move] = self._search(
                    game, depth=1, alpha=-math.inf, beta=math.inf
                )
            finally:
                game.undo_move(move)

        best_score = max(self.candidate_scores.values())
        return min(move for move, score in self.candidate_scores.items() if score == best_score)

    def _terminal_score(self, game: TicTacToe, depth: int) -> int | None:
        winner = game.check_winner()
        if winner == self.player:
            return 10 - depth
        if winner is not None:
            return depth - 10
        if game.is_draw():
            return 0
        return None

    def _search(self, game: TicTacToe, depth: int, alpha: float, beta: float) -> int:
        self.nodes_visited += 1
        terminal_score = self._terminal_score(game, depth)
        if terminal_score is not None:
            return terminal_score

        maximizing = game.current_player == self.player
        best_score = -math.inf if maximizing else math.inf
        for move in game.get_available_moves():
            game.make_move(move, game.current_player)
            try:
                score = self._search(game, depth + 1, alpha, beta)
            finally:
                game.undo_move(move)

            if maximizing:
                best_score = max(best_score, score)
                alpha = max(alpha, best_score)
            else:
                best_score = min(best_score, score)
                beta = min(beta, best_score)

            if self.use_alpha_beta and alpha >= beta:
                self.alpha_beta_cutoffs += 1
                break

        return int(best_score)


def simulate_match(agent1, agent2, num_games: int = 1) -> dict[str, int]:
    """Play ``num_games`` with each agent assigned its configured symbol.

    Returns counts under ``agent1_wins``, ``agent2_wins``, and ``draws``.
    The agents must have different ``player`` symbols.
    """
    if not isinstance(num_games, int) or isinstance(num_games, bool) or num_games < 0:
        raise ValueError("num_games must be a non-negative integer")
    if agent1.player == agent2.player:
        raise ValueError("agents must use different player symbols")

    outcomes = {"agent1_wins": 0, "agent2_wins": 0, "draws": 0}
    agents = {agent1.player: agent1, agent2.player: agent2}

    for _ in range(num_games):
        game = TicTacToe()
        while not game.is_game_over():
            current_agent = agents[game.current_player]
            move = current_agent.get_move(game)
            game.make_move(move, current_agent.player)

        winner = game.check_winner()
        if winner is None:
            outcomes["draws"] += 1
        elif winner == agent1.player:
            outcomes["agent1_wins"] += 1
        else:
            outcomes["agent2_wins"] += 1

    return outcomes
