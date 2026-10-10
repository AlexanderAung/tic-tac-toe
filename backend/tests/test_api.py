"""Integration tests for the Flask game-session API."""

import importlib
import pytest

from backend.app import app, games
from backend.game import TicTacToe


@pytest.fixture
def client():
    games.clear()
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client
    games.clear()


def create(client, symbol="X", difficulty=None):
    payload = {"player_symbol": symbol}
    if difficulty is not None:
        payload["difficulty"] = difficulty
    response = client.post("/games", json=payload)
    assert response.status_code == 201
    return response.get_json()


def test_create_game_for_either_human_symbol(client):
    x_game = create(client, "X")
    assert x_game["player_symbol"] == "X"
    assert x_game["ai_symbol"] == "O"
    assert x_game["board"] == [["", "", ""] for _ in range(3)]
    assert x_game["next_turn"] == "human"

    o_game = create(client, "O")
    assert o_game["player_symbol"] == "O"
    assert o_game["ai_symbol"] == "X"
    assert sum(cell != "" for row in o_game["board"] for cell in row) == 1
    assert sum(cell == "X" for row in o_game["board"] for cell in row) == 1
    assert o_game["next_turn"] == "human"


@pytest.mark.parametrize(
    ("difficulty", "agent_type"),
    [("easy", "RandomAgent"), ("medium", "HeuristicAgent"), ("hard", "MinimaxAgent")],
)
def test_difficulty_selects_agent(client, difficulty, agent_type):
    state = create(client, difficulty=difficulty)
    assert games[state["game_id"]].difficulty == difficulty
    assert type(games[state["game_id"]].agent).__name__ == agent_type


def test_default_difficulty_is_medium(client):
    state = create(client)
    assert games[state["game_id"]].difficulty == "medium"


def test_human_move_and_ai_move_are_applied_by_engine(client):
    state = create(client, difficulty="easy")
    response = client.post(
        f"/games/{state['game_id']}/moves", json={"row": 0, "col": 0}
    )
    assert response.status_code == 200
    updated = response.get_json()
    assert updated["board"][0][0] == "X"
    assert sum(cell != "" for row in updated["board"] for cell in row) == 2
    assert updated["next_turn"] == "human"
    assert games[state["game_id"]].game.board == [cell for row in updated["board"] for cell in row]


@pytest.mark.parametrize(
    "payload",
    [
        {"row": -1, "col": 0},
        {"row": 3, "col": 0},
        {"row": 0, "col": 3},
        {"row": 1.5, "col": 0},
        {"row": True, "col": 0},
        {"row": 0},
    ],
)
def test_invalid_coordinates_do_not_mutate_board(client, payload):
    state = create(client)
    before = client.get(f"/games/{state['game_id']}").get_json()
    response = client.post(f"/games/{state['game_id']}/moves", json=payload)
    assert response.status_code == 400
    after = client.get(f"/games/{state['game_id']}").get_json()
    assert after["board"] == before["board"]


def test_occupied_cell_is_rejected_without_mutation(client):
    state = create(client, "O")  # medium AI opens in the center
    assert state["board"][1][1] == "X"
    response = client.post(
        f"/games/{state['game_id']}/moves", json={"row": 1, "col": 1}
    )
    assert response.status_code == 409
    assert client.get(f"/games/{state['game_id']}").get_json()["board"] == state["board"]


def test_unknown_game_ids_return_consistent_json_errors(client):
    missing = "no-such-game"
    assert client.get(f"/games/{missing}").get_json() == {"error": "Game not found"}
    response = client.post(f"/games/{missing}/moves", json={"row": 0, "col": 0})
    assert response.status_code == 404
    assert response.get_json() == {"error": "Game not found"}


def test_get_returns_current_game_state(client):
    created = create(client)
    client.post(f"/games/{created['game_id']}/moves", json={"row": 0, "col": 0})
    response = client.get(f"/games/{created['game_id']}")
    assert response.status_code == 200
    assert response.get_json()["board"][0][0] == "X"


def test_human_win_skips_ai_and_rejects_later_moves(client):
    state = create(client, "X", "easy")
    session = games[state["game_id"]]
    session.game = TicTacToe(["X", "X", "", "O", "O", "", "", "", ""], "X")
    session.agent.get_move = lambda game: pytest.fail("AI must not move after a terminal state")

    response = client.post(
        f"/games/{state['game_id']}/moves", json={"row": 0, "col": 2}
    )
    assert response.status_code == 200
    assert response.get_json()["status"] == "won"
    assert response.get_json()["winner"] == "X"
    assert response.get_json()["next_turn"] is None

    after_end = client.post(
        f"/games/{state['game_id']}/moves", json={"row": 2, "col": 2}
    )
    assert after_end.status_code == 409


def test_draw_skips_ai(client):
    state = create(client, "X", "easy")
    games[state["game_id"]].game = TicTacToe(
        ["X", "O", "X", "X", "O", "O", "O", "X", ""], "X"
    )
    games[state["game_id"]].agent.get_move = lambda game: pytest.fail(
        "AI must not move after a draw"
    )

    response = client.post(
        f"/games/{state['game_id']}/moves", json={"row": 2, "col": 2}
    )
    assert response.status_code == 200
    assert response.get_json()["status"] == "draw"
    assert response.get_json()["winner"] is None
    assert response.get_json()["next_turn"] is None


def test_simultaneous_sessions_have_independent_boards(client):
    first = create(client, difficulty="easy")
    second = create(client, difficulty="easy")
    client.post(f"/games/{first['game_id']}/moves", json={"row": 0, "col": 0})

    first_board = client.get(f"/games/{first['game_id']}").get_json()["board"]
    second_board = client.get(f"/games/{second['game_id']}").get_json()["board"]
    assert first_board != second_board
    assert second_board == [["", "", ""] for _ in range(3)]


def test_invalid_create_requests_return_json_errors(client):
    for payload in ({}, {"player_symbol": "Z"}, {"player_symbol": "X", "difficulty": "expert"}):
        response = client.post("/games", json=payload)
        assert response.status_code == 400
        assert isinstance(response.get_json().get("error"), str)


def test_production_frontend_files_are_served_from_the_app(client, tmp_path, monkeypatch):
    backend_app = importlib.import_module("backend.app")
    assets = tmp_path / "assets"
    assets.mkdir()
    (tmp_path / "index.html").write_text("<main>game client</main>")
    (assets / "app.js").write_text("console.log('loaded')")
    monkeypatch.setattr(backend_app, "FRONTEND_DIST", tmp_path)

    page = client.get("/")
    script = client.get("/assets/app.js")
    health = client.get("/api/health")
    assert page.status_code == 200
    assert b"game client" in page.data
    assert script.status_code == 200
    assert b"loaded" in script.data
    assert health.status_code == 200
