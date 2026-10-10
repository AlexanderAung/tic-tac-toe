"""Flask API for in-memory Tic-Tac-Toe games."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
import uuid

from flask import Flask, jsonify, request, send_from_directory

if __package__:
    from .agent import HeuristicAgent, MinimaxAgent, RandomAgent
    from .game import TicTacToe
else:  # Support ``python backend/app.py`` as well as package-based imports.
    project_root = str(Path(__file__).resolve().parents[1])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from backend.agent import HeuristicAgent, MinimaxAgent, RandomAgent
    from backend.game import TicTacToe

app = Flask(__name__)
FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"


@dataclass
class GameSession:
    game: TicTacToe
    player_symbol: str
    ai_symbol: str
    difficulty: str
    agent: RandomAgent | HeuristicAgent | MinimaxAgent


# This store is intentionally process-local; sessions expire when the process restarts.
games: dict[str, GameSession] = {}

DIFFICULTY_AGENTS = {
    "easy": RandomAgent,
    "medium": HeuristicAgent,
    "hard": MinimaxAgent,
}


@app.route("/")
def hello_world():
    if (FRONTEND_DIST / "index.html").is_file():
        return send_from_directory(FRONTEND_DIST, "index.html")
    return "<p>Hello, World!</p>"


@app.get("/<path:filename>")
def frontend_asset(filename: str):
    if (FRONTEND_DIST / filename).is_file():
        return send_from_directory(FRONTEND_DIST, filename)
    return _error("Not found", 404)


@app.get("/api/health")
def health():
    return {"status": "ok", "message": "Flask is connected!"}


def _state_response(game_id: str, session: GameSession):
    game = session.game
    winner = game.check_winner()
    if winner is not None:
        status = "won"
    elif game.is_draw():
        status = "draw"
    else:
        status = "in_progress"

    next_turn = None if status != "in_progress" else (
        "human" if game.current_player == session.player_symbol else "ai"
    )
    return {
        "game_id": game_id,
        "player_symbol": session.player_symbol,
        "ai_symbol": session.ai_symbol,
        "board": [game.board[row * 3 : row * 3 + 3] for row in range(3)],
        "status": status,
        "next_turn": next_turn,
        "winner": winner,
    }


def _error(message: str, status: int):
    return jsonify(error=message), status


def _choose_agent(difficulty: str, player: str):
    return DIFFICULTY_AGENTS[difficulty](player)


@app.post("/games")
def create_game():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _error("Request body must be a JSON object", 400)

    player_symbol = data.get("player_symbol")
    if not isinstance(player_symbol, str) or player_symbol not in {"X", "O"}:
        return _error("player_symbol must be X or O", 400)

    difficulty = data.get("difficulty", "medium")
    if not isinstance(difficulty, str) or difficulty not in DIFFICULTY_AGENTS:
        return _error("difficulty must be easy, medium, or hard", 400)

    ai_symbol = "O" if player_symbol == "X" else "X"
    game = TicTacToe()
    session = GameSession(
        game=game,
        player_symbol=player_symbol,
        ai_symbol=ai_symbol,
        difficulty=difficulty,
        agent=_choose_agent(difficulty, ai_symbol),
    )
    game_id = str(uuid.uuid4())
    games[game_id] = session

    # X always starts. When the human selects O, let the AI open through the engine.
    if player_symbol == "O":
        ai_move = session.agent.get_move(game)
        game.make_move(ai_move, ai_symbol)

    return jsonify(_state_response(game_id, session)), 201


@app.post("/games/<game_id>/moves")
def make_move(game_id: str):
    session = games.get(game_id)
    if session is None:
        return _error("Game not found", 404)

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _error("Request body must be a JSON object", 400)
    row, col = data.get("row"), data.get("col")
    if any(not isinstance(value, int) or isinstance(value, bool) for value in (row, col)):
        return _error("row and col must be integers from 0 through 2", 400)
    if not (0 <= row < 3 and 0 <= col < 3):
        return _error("row and col must be integers from 0 through 2", 400)

    game = session.game
    if game.is_game_over():
        return _error("Game has already ended", 409)

    position = row * 3 + col
    if not game.is_valid_move(position, session.player_symbol):
        return _error("Move is not legal", 409)

    # The engine remains the only component that mutates a board.
    game.make_move(position, session.player_symbol)
    if not game.is_game_over():
        ai_move = session.agent.get_move(game)
        game.make_move(ai_move, session.ai_symbol)

    return jsonify(_state_response(game_id, session)), 200


@app.get("/games/<game_id>")
def get_game(game_id: str):
    session = games.get(game_id)
    if session is None:
        return _error("Game not found", 404)
    return jsonify(_state_response(game_id, session)), 200


if __name__ == "__main__":
    app.run(debug=False)
