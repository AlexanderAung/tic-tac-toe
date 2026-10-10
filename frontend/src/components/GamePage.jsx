import { useState } from 'react';
import Board from './Board';
import StatusBanner from './StatusBanner';

const EMPTY_BOARD = Array(9).fill(null);
export default function GamePage() {
  const [gameId, setGameId]       = useState(null);
  const [board, setBoard]         = useState(EMPTY_BOARD);
  const [winner, setWinner]       = useState(null); // null | 'X' | 'O' | 'draw'
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState('');

  // On mount: create a new game
  async function startNewGame() {
    setLoading(true);
    setError('');
    try {
      const res = await fetch('/games', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player_symbol: 'X' }),
      });
      if (!res.ok) throw new Error(`HTTP error: ${res.status}`);

      const data = await res.json();
      setGameId(data.game_id);
      setBoard(data.board?.flat() ?? [...EMPTY_BOARD]);
      setWinner(data.status === 'draw' ? 'draw' : data.winner ?? null);
    } catch (err) {
      setError('Could not start a new game. Check that the Flask backend is running on port 5000.');
      console.error('Could not start a new game:', err);
    } finally {
      setLoading(false);
    }
  }

  // Called by Board when a square is clicked
  async function handleSquareClick(index) {
    if (winner || board[index] || loading) return;

    setError('');
    setLoading(true);
    try {
      const res = await fetch(`/games/${gameId}/moves`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ row: Math.floor(index / 3), col: index % 3 }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? `HTTP error: ${res.status}`);

      setBoard(data.board.flat());
      setWinner(data.status === 'draw' ? 'draw' : data.winner ?? null);
    } catch (err) {
      setError('Could not make that move. Please try again.');
      console.error('Could not make a move:', err);
    } finally {
      setLoading(false);
    }
  }

  if (!gameId) {
    return (
      <div>
        <h1>Tic-Tac-Toe</h1>
        {error && <p role="alert">{error}</p>}
        <button onClick={startNewGame} disabled={loading}>
          {loading ? 'Starting…' : 'Start New Game'}
        </button>
      </div>
    );
  }

  return (
    <div>
      <h1>Tic-Tac-Toe</h1>
      {error && <p role="alert">{error}</p>}
      <StatusBanner board={board} winner={winner} />
      <Board board={board} onSquareClick={handleSquareClick} />
      <button onClick={startNewGame}>New Game</button>
    </div>
  );
}
