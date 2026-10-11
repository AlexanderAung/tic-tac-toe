"""Flask API for in-memory Tic-Tac-Toe games."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
import uuid

from flask import Flask, jsonify, request, send_from_directory

if __package__:
    from .agent import HeuristicAgent, MinimaxAgent, RandomAgent, simulate_match
    from .game import TicTacToe
else:  # Support ``python backend/app.py`` as well as package-based imports.
    project_root = str(Path(__file__).resolve().parents[1])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from backend.agent import HeuristicAgent, MinimaxAgent, RandomAgent, simulate_match
    from backend.game import TicTacToe

app = Flask(__name__)
FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"


@dataclass
class GameSession:
    game: TicTacToe
    player_symbol: str
    ai_symbol: str
    difficulty: str
    agent: RandomAgent | HeuristicAgent | MinimaxAgent | None
    mode: str = "human_ai"
    opponent_agent: RandomAgent | HeuristicAgent | MinimaxAgent | None = None


# This store is intentionally process-local; sessions expire when the process restarts.
games: dict[str, GameSession] = {}

DIFFICULTY_AGENTS = {
    "easy": RandomAgent,
    "medium": HeuristicAgent,
    "hard": MinimaxAgent,
}

GAME_MODES = {"human_ai", "two_player", "ai_vs_ai"}


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

    if status != "in_progress":
        next_turn = None
    elif session.mode in {"two_player", "ai_vs_ai"}:
        next_turn = "human" if session.mode == "two_player" else "ai"
    else:
        next_turn = "human" if game.current_player == session.player_symbol else "ai"
    analysis = {"scores": {}, "nodes": 0, "cutoffs": 0}
    if status == "in_progress":
        analyzer = MinimaxAgent(game.current_player)
        analyzer.get_move(TicTacToe(game.board, current_player=game.current_player))
        analysis = {
            "scores": analyzer.candidate_scores,
            "nodes": analyzer.nodes_visited,
            "cutoffs": analyzer.alpha_beta_cutoffs,
        }
    return {
        "game_id": game_id,
        "player_symbol": session.player_symbol,
        "ai_symbol": session.ai_symbol,
        "board": [game.board[row * 3 : row * 3 + 3] for row in range(3)],
        "status": status,
        "next_turn": next_turn,
        "winner": winner,
        "mode": session.mode,
        "current_player": game.current_player if status == "in_progress" else None,
        "analysis": analysis,
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

    mode = data.get("mode", "human_ai")
    opponent_difficulty = data.get("opponent_difficulty", difficulty)
    if mode not in GAME_MODES:
        return _error("mode must be human_ai, two_player, or ai_vs_ai", 400)
    if opponent_difficulty not in DIFFICULTY_AGENTS:
        return _error("opponent_difficulty must be easy, medium, or hard", 400)

    ai_symbol = "O" if player_symbol == "X" else "X"
    game = TicTacToe()
    if mode == "ai_vs_ai":
        agent = _choose_agent(difficulty, "X")
        opponent_agent = _choose_agent(opponent_difficulty, "O")
    elif mode == "two_player":
        agent = opponent_agent = None
    else:
        agent = _choose_agent(difficulty, ai_symbol)
        opponent_agent = None
    session = GameSession(
        game=game,
        player_symbol=player_symbol,
        ai_symbol=ai_symbol,
        difficulty=difficulty,
        agent=agent,
        mode=mode,
        opponent_agent=opponent_agent,
    )
    game_id = str(uuid.uuid4())
    games[game_id] = session

    # X always starts. When the human selects O, let the AI open through the engine.
    if mode == "human_ai" and player_symbol == "O":
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
    if session.mode == "ai_vs_ai":
        return _error("AI vs AI games use the AI move endpoint", 409)
    move_symbol = game.current_player if session.mode == "two_player" else session.player_symbol
    if not game.is_valid_move(position, move_symbol):
        return _error("Move is not legal", 409)

    # The engine remains the only component that mutates a board.
    game.make_move(position, move_symbol)
    if session.mode == "human_ai" and not game.is_game_over():
        ai_move = session.agent.get_move(game)
        game.make_move(ai_move, session.ai_symbol)

    return jsonify(_state_response(game_id, session)), 200


@app.post("/games/<game_id>/ai-move")
def make_ai_move(game_id: str):
    session = games.get(game_id)
    if session is None:
        return _error("Game not found", 404)
    game = session.game
    if game.is_game_over():
        return _error("Game has already ended", 409)
    if session.mode == "human_ai" and game.current_player == session.player_symbol:
        return _error("It is the human player's turn", 409)
    if session.mode == "ai_vs_ai":
        agent = session.agent if game.current_player == "X" else session.opponent_agent
    else:
        agent = session.agent
    if agent is None:
        return _error("This game mode has no AI turn", 409)
    game.make_move(agent.get_move(game), game.current_player)
    return jsonify(_state_response(game_id, session)), 200


@app.post("/benchmark")
def benchmark():
    data = request.get_json(silent=True) or {}
    difficulty_1 = data.get("difficulty_1", "easy")
    difficulty_2 = data.get("difficulty_2", "hard")
    num_games = data.get("num_games", 10)
    if difficulty_1 not in DIFFICULTY_AGENTS or difficulty_2 not in DIFFICULTY_AGENTS:
        return _error("Choose easy, medium, or hard for both agents", 400)
    if not isinstance(num_games, int) or isinstance(num_games, bool) or num_games < 1:
        return _error("num_games must be a positive integer", 400)
    results = simulate_match(
        _choose_agent(difficulty_1, "X"),
        _choose_agent(difficulty_2, "O"),
        num_games,
    )
    return jsonify({
        **results,
        "games": num_games,
        "agent1_rate": results["agent1_wins"] / num_games,
        "agent2_rate": results["agent2_wins"] / num_games,
        "draw_rate": results["draws"] / num_games,
    })


@app.get("/games/<game_id>")
def get_game(game_id: str):
    session = games.get(game_id)
    if session is None:
        return _error("Game not found", 404)
    return jsonify(_state_response(game_id, session)), 200


if __name__ == "__main__":
    app.run(debug=False)
