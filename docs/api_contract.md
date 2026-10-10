# Tic-Tac-Toe API Contract

## 1. Overview

The API manages Tic-Tac-Toe games between a human player and an AI opponent.

* Backend: Flask
* Frontend: React
* The backend is the source of truth for game state.
* The frontend must not send or modify the board directly.
* The AI uses a game-playing algorithm to choose its moves.

## 2. Game Rules

* The board is a 3×3 grid.
* The human chooses either `X` or `O`.
* The AI uses the other symbol.
* `X` always moves first.
* The backend makes the AI's opening move when the human chooses `O`.
* A game ends when a player gets three symbols in a row, column, or diagonal, or when the board is full with no winner.
* No moves are allowed after the game ends.

## 3. Data Conventions

### Symbols

* `X`
* `O`
* Empty cells are represented by an empty string `""`.

### Game status

* `in_progress`
* `won`
* `draw`

### Next turn

* `human`
* `ai`
* `null` when the game is over.

## 4. Endpoints

### 4.1 Create a Game

**Method:** `POST`

**Path:** `/games`

**Purpose:** Create a new game.

**Request body:**

```json
{
  "player_symbol": "X",
  "difficulty": "medium"
}
```

`player_symbol` must be `X` or `O`.
`difficulty` is optional and accepts `easy`, `medium`, or `hard`; it defaults to
`medium` when omitted. These values select the `RandomAgent`, `HeuristicAgent`,
and `MinimaxAgent`, respectively.

**Successful response:** `201 Created`

```json
{
  "game_id": "abc123",
  "player_symbol": "X",
  "ai_symbol": "O",
  "board": [
    ["", "", ""],
    ["", "", ""],
    ["", "", ""]
  ],
  "status": "in_progress",
  "next_turn": "human",
  "winner": null
}
```

If the human chooses `O`, the backend makes the AI's opening move before returning the response.

**Errors:**

* `400 Bad Request`: Invalid JSON, missing or invalid `player_symbol`, or an
  unsupported `difficulty`.

### 4.2 Make a Move

**Method:** `POST`

**Path:** `/games/{game_id}/moves`

**Purpose:** Submit a human move. The backend validates the move, updates the board, checks the outcome, and makes an AI move if the game is still in progress.

**Request body:**

```json
{
  "row": 1,
  "col": 1
}
```

Rows and columns use zero-based indexing: `0`, `1`, or `2`.

**Successful response:** `200 OK`

```json
{
  "game_id": "abc123",
  "player_symbol": "X",
  "ai_symbol": "O",
  "board": [
    ["", "", ""],
    ["", "X", ""],
    ["", "", "O"]
  ],
  "status": "in_progress",
  "next_turn": "human",
  "winner": null
}
```

The board shown is illustrative. The actual AI move depends on the algorithm.

**Errors:**

* `400 Bad Request`: Invalid or missing row/column values.
* `404 Not Found`: The game does not exist.
* `409 Conflict`: The target cell is occupied or the game has already ended.

An invalid move must not change the stored game state.

### 4.3 Get a Game

**Method:** `GET`

**Path:** `/games/{game_id}`

**Purpose:** Retrieve the current state of a game.

**Successful response:** `200 OK`

Returns the same game-state structure used by the other endpoints.

**Errors:**

* `404 Not Found`: The game does not exist.

### Error response

All errors use a JSON object with an `error` string, for example:

```json
{"error": "Game not found"}
```

## 5. Game-State Response Fields

| Field           | Type           | Meaning                         |
| --------------- | -------------- | ------------------------------- |
| `game_id`       | string         | Unique identifier for the game  |
| `player_symbol` | string         | Human player's symbol           |
| `ai_symbol`     | string         | AI's symbol                     |
| `board`         | array          | Three rows of three cells       |
| `status`        | string         | `in_progress`, `won`, or `draw` |
| `next_turn`     | string or null | `human`, `ai`, or null          |
| `winner`        | string or null | `X`, `O`, or null               |

## 6. Play Again

When the player clicks **Play again**, the frontend calls `POST /games` again. The backend creates a new game with a new `game_id`. The previous game is not restarted.

## 7. Implementation Scope

For the initial version, game state may be stored in server memory. Games will not survive a backend restart, and multiple application workers will not automatically share state. Persistent storage can be added later if needed.
