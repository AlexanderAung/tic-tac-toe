from functools import lru_cache
import random

import pytest

from backend.agent import HeuristicAgent, MinimaxAgent, RandomAgent, simulate_match
from backend.game import EMPTY, PLAYER_O, PLAYER_X, TicTacToe

REFERENCE_LINES = (
    (0, 1, 2), (3, 4, 5), (6, 7, 8),
    (0, 3, 6), (1, 4, 7), (2, 5, 8),
    (0, 4, 8), (2, 4, 6),
)


def test_random_agent_selects_only_available_moves_and_rejects_terminal_state():
    game = TicTacToe()
    agent = RandomAgent(PLAYER_X, rng=random.Random(17))
    for _ in range(20):
        move = agent.get_move(game)
        assert move in game.get_available_moves()

    finished = TicTacToe([
        PLAYER_X, PLAYER_O, PLAYER_X,
        PLAYER_X, PLAYER_O, PLAYER_O,
        PLAYER_O, PLAYER_X, PLAYER_X,
    ])
    with pytest.raises(ValueError, match="finished game"):
        agent.get_move(finished)


def test_agents_reject_calls_outside_their_turn():
    game = TicTacToe()
    with pytest.raises(ValueError, match="not O's"):
        RandomAgent(PLAYER_O).get_move(game)


def test_heuristic_takes_immediate_win_and_blocks_immediate_loss():
    win = TicTacToe([
        PLAYER_O, PLAYER_O, EMPTY,
        PLAYER_X, PLAYER_X, EMPTY,
        EMPTY, EMPTY, EMPTY,
    ], current_player=PLAYER_O)
    block = TicTacToe([
        PLAYER_X, PLAYER_X, EMPTY,
        PLAYER_O, EMPTY, EMPTY,
        EMPTY, EMPTY, EMPTY,
    ], current_player=PLAYER_O)
    agent = HeuristicAgent(PLAYER_O, rng=random.Random(1))

    assert agent.get_move(win) == 2
    assert agent.get_move(block) == 2


def test_heuristic_uses_center_then_randomized_corners_without_mutating_game():
    agent = HeuristicAgent(PLAYER_X, rng=random.Random(11))
    empty = TicTacToe()
    board_before = empty.board.copy()
    assert agent.get_move(empty) == 4
    assert empty.board == board_before

    corner_position = TicTacToe(
        [PLAYER_X, EMPTY, EMPTY,
         EMPTY, PLAYER_O, EMPTY,
         EMPTY, EMPTY, EMPTY],
        current_player=PLAYER_X,
    )
    assert agent.get_move(corner_position) in HeuristicAgent.CORNERS[1:]


def test_minimax_takes_win_blocks_loss_and_prefers_forced_draw():
    agent = MinimaxAgent(PLAYER_O)
    win = TicTacToe([
        PLAYER_O, PLAYER_O, EMPTY,
        PLAYER_X, PLAYER_X, EMPTY,
        EMPTY, EMPTY, EMPTY,
    ], current_player=PLAYER_O)
    block = TicTacToe([
        PLAYER_X, PLAYER_X, EMPTY,
        PLAYER_O, EMPTY, EMPTY,
        EMPTY, EMPTY, EMPTY,
    ], current_player=PLAYER_O)

    assert agent.get_move(win) == 2
    assert agent.get_move(block) == 2

    opening = MinimaxAgent(PLAYER_X)
    opening.get_move(TicTacToe())
    assert max(opening.candidate_scores.values()) == 0


def test_minimax_returns_legal_deterministic_moves_and_resets_statistics():
    game = TicTacToe()
    agent = MinimaxAgent(PLAYER_X)
    snapshot = (game.board.copy(), game.current_player)

    move1 = agent.get_move(game)
    first_scores = agent.candidate_scores.copy()
    first_nodes = agent.nodes_visited
    first_cutoffs = agent.alpha_beta_cutoffs
    move2 = agent.get_move(game)

    assert move1 == move2 == 0
    assert set(first_scores) == set(range(9))
    assert agent.candidate_scores == first_scores
    assert first_nodes > 0
    assert first_cutoffs > 0
    assert agent.alpha_beta_cutoffs == first_cutoffs
    assert agent.nodes_visited == first_nodes
    assert (game.board, game.current_player) == snapshot


def test_alpha_beta_root_scores_match_independent_unpruned_reference_for_all_states():
    @lru_cache(maxsize=None)
    def reference_value(board: tuple[str, ...], to_move: str, player: str, depth: int) -> int:
        winner = None
        for line in REFERENCE_LINES:
            symbol = board[line[0]]
            if symbol in (PLAYER_X, PLAYER_O) and all(board[pos] == symbol for pos in line[1:]):
                winner = symbol
                break
        if winner == player:
            return 10 - depth
        if winner is not None:
            return depth - 10
        legal_moves = [pos for pos, cell in enumerate(board) if cell == EMPTY]
        if not legal_moves:
            return 0

        next_player = PLAYER_O if to_move == PLAYER_X else PLAYER_X
        child_values = []
        for move in legal_moves:
            child = list(board)
            child[move] = to_move
            child_values.append(reference_value(tuple(child), next_player, player, depth + 1))
        return max(child_values) if to_move == player else min(child_values)

    reachable_states: set[tuple[tuple[str, ...], str]] = set()

    def collect_states(game: TicTacToe) -> None:
        if game.is_game_over():
            return
        reachable_states.add((tuple(game.board), game.current_player))
        for move in game.get_available_moves():
            game.make_move(move)
            try:
                collect_states(game)
            finally:
                game.undo_move(move)

    collect_states(TicTacToe())
    for board, to_move in reachable_states:
        game = TicTacToe(board, current_player=to_move)
        agent = MinimaxAgent(to_move)
        move = agent.get_move(game)
        expected = reference_value(board, to_move, to_move, 0)

        assert move in game.get_available_moves()
        assert agent.candidate_scores[move] == expected
        assert max(agent.candidate_scores.values()) == expected
        assert game.board == list(board)
        assert game.current_player == to_move


@pytest.mark.parametrize("ai_symbol", [PLAYER_X, PLAYER_O])
def test_minimax_never_loses_against_any_legal_opponent_play(ai_symbol):
    agent = MinimaxAgent(ai_symbol)
    opponent = PLAYER_O if ai_symbol == PLAYER_X else PLAYER_X

    def opponent_can_force_win(game: TicTacToe) -> bool:
        winner = game.check_winner()
        if winner is not None:
            return winner == opponent
        if game.is_draw():
            return False

        if game.current_player == ai_symbol:
            move = agent.get_move(game)
            game.make_move(move, ai_symbol)
            try:
                return opponent_can_force_win(game)
            finally:
                game.undo_move(move)

        for move in game.get_available_moves():
            game.make_move(move, opponent)
            try:
                if opponent_can_force_win(game):
                    return True
            finally:
                game.undo_move(move)
        return False

    assert not opponent_can_force_win(TicTacToe())


def test_match_helper_reports_all_outcomes():
    outcomes = simulate_match(
        MinimaxAgent(PLAYER_X),
        RandomAgent(PLAYER_O, rng=random.Random(4)),
        num_games=4,
    )
    assert set(outcomes) == {"agent1_wins", "agent2_wins", "draws"}
    assert sum(outcomes.values()) == 4
    assert outcomes["agent2_wins"] == 0
