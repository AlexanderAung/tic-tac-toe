import pytest

from backend.game import EMPTY, PLAYER_O, PLAYER_X, WINNING_LINES, TicTacToe


def test_initial_board_and_available_moves():
    game = TicTacToe()

    assert game.board == [EMPTY] * 9
    assert game.current_player == PLAYER_X
    assert game.get_available_moves() == list(range(9))
    assert game.check_winner() is None
    assert not game.is_draw()
    assert not game.is_game_over()


def test_make_move_and_lifo_undo_restore_board_and_turn():
    game = TicTacToe()
    original = (game.board.copy(), game.current_player)

    assert game.make_move(4, PLAYER_X) is True
    assert game.board[4] == PLAYER_X
    assert game.current_player == PLAYER_O
    assert game.make_move(0) is True
    assert game.current_player == PLAYER_X

    with pytest.raises(ValueError, match="reverse order"):
        game.undo_move(4)

    assert game.undo_move(0) is True
    assert game.undo_move(4) is True
    assert (game.board, game.current_player) == original


@pytest.mark.parametrize("pos", [-1, 9, 1.5, True, "0", None])
def test_invalid_positions_are_rejected(pos):
    game = TicTacToe()
    with pytest.raises(ValueError, match="pos must be"):
        game.make_move(pos)
    assert game.board == [EMPTY] * 9


@pytest.mark.parametrize("symbol", ["x", "", "Z"])
def test_invalid_players_are_rejected(symbol):
    game = TicTacToe()
    with pytest.raises(ValueError, match="player must"):
        game.make_move(0, symbol)
    assert game.board == [EMPTY] * 9


def test_out_of_turn_and_occupied_moves_are_rejected_without_mutation():
    game = TicTacToe()
    game.make_move(0, PLAYER_X)
    before = (game.board.copy(), game.current_player)

    assert not game.is_valid_move(0)
    assert not game.is_valid_move(1, PLAYER_X)
    with pytest.raises(ValueError, match="already occupied"):
        game.make_move(0, PLAYER_O)
    with pytest.raises(ValueError, match="it is O's turn"):
        game.make_move(1, PLAYER_X)
    assert (game.board, game.current_player) == before


def test_every_winning_line_and_winning_line_order():
    for line in WINNING_LINES:
        board = [EMPTY] * 9
        for pos in line:
            board[pos] = PLAYER_X
        game = TicTacToe(board)
        assert game.check_winner() == PLAYER_X
        assert game.get_winning_line() == line
        assert game.is_game_over()
        assert not game.is_draw()
        assert game.get_available_moves() == []


def test_winning_move_is_terminal_until_explicit_undo():
    game = TicTacToe([PLAYER_X, PLAYER_X, EMPTY, PLAYER_O, PLAYER_O, EMPTY,
                      EMPTY, EMPTY, EMPTY], current_player=PLAYER_X)
    before = game.board.copy()

    game.make_move(2)
    assert game.check_winner() == PLAYER_X
    assert game.is_game_over()
    assert game.get_available_moves() == []
    with pytest.raises(ValueError, match="game has ended"):
        game.make_move(5)

    # Undo is an explicit search rollback, restoring the exact live position.
    game.undo_move(2)
    assert game.board == before
    assert game.current_player == PLAYER_X
    assert not game.is_game_over()


def test_draw_requires_full_board_and_no_winner():
    draw = TicTacToe([
        PLAYER_X, PLAYER_O, PLAYER_X,
        PLAYER_X, PLAYER_O, PLAYER_O,
        PLAYER_O, PLAYER_X, PLAYER_X,
    ])
    partial = TicTacToe([PLAYER_X, PLAYER_O, PLAYER_X,
                         PLAYER_X, PLAYER_O, PLAYER_O,
                         PLAYER_O, PLAYER_X, EMPTY])

    assert draw.check_winner() is None
    assert draw.is_draw()
    assert draw.is_game_over()
    assert not partial.is_draw()
    with pytest.raises(ValueError, match="game has ended"):
        draw.make_move(0)


def test_constructor_validates_and_copies_board():
    supplied = [EMPTY] * 9
    game = TicTacToe(supplied)
    supplied[0] = PLAYER_X
    assert game.board == [EMPTY] * 9

    with pytest.raises(ValueError, match="exactly nine"):
        TicTacToe([EMPTY] * 8)
    with pytest.raises(ValueError, match="board cells"):
        TicTacToe(["?"] + [EMPTY] * 8)
    with pytest.raises(ValueError, match="current_player"):
        TicTacToe(current_player="?")


def test_undo_requires_a_move_made_through_this_instance():
    game = TicTacToe([PLAYER_X] + [EMPTY] * 8, current_player=PLAYER_O)
    with pytest.raises(ValueError, match="no move to undo"):
        game.undo_move(0)
