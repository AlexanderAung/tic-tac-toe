import { useCallback, useEffect, useState } from 'react';
import Board from './Board';

const MODES = [
  { value: 'human_ai', label: 'Human vs AI' },
  { value: 'two_player', label: '2-Player Local' },
  { value: 'ai_vs_ai', label: 'AI vs AI' },
];
const DIFFICULTIES = [
  { value: 'easy', label: 'Easy' },
  { value: 'medium', label: 'Medium' },
  { value: 'hard', label: 'Unbeatable' },
];

async function postJson(url, body) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const responseText = await response.text();
  let data;
  try {
    data = JSON.parse(responseText);
  } catch {
    throw new Error(`Server returned an unexpected response (${response.status}). Check that the Flask backend is running.`);
  }
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}

export default function GamePage() {
  const [mode, setMode] = useState('human_ai');
  const [difficulty, setDifficulty] = useState('medium');
  const [opponentDifficulty, setOpponentDifficulty] = useState('hard');
  const [playerSymbol, setPlayerSymbol] = useState('X');
  const [game, setGame] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [autoPlay, setAutoPlay] = useState(false);
  const [benchmarkSize, setBenchmarkSize] = useState(50);
  const [benchmarkAgents, setBenchmarkAgents] = useState(['easy', 'hard']);
  const [benchmark, setBenchmark] = useState(null);
  const [benchmarkProgress, setBenchmarkProgress] = useState(0);

  const startGame = async () => {
    setBusy(true);
    setError('');
    setAutoPlay(false);
    try {
      const data = await postJson('/games', {
        mode,
        difficulty,
        opponent_difficulty: opponentDifficulty,
        player_symbol: playerSymbol,
      });
      setGame(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const makeAiMove = useCallback(async () => {
    if (!game?.game_id) return;
    try {
      const data = await postJson(`/games/${game.game_id}/ai-move`, {});
      setGame(data);
      if (data.status !== 'in_progress') setAutoPlay(false);
    } catch (err) {
      setError(err.message);
      setAutoPlay(false);
    }
  }, [game?.game_id]);

  useEffect(() => {
    if (!autoPlay || game?.mode !== 'ai_vs_ai' || game?.status !== 'in_progress' || busy) return undefined;
    const timer = window.setTimeout(makeAiMove, 450);
    return () => window.clearTimeout(timer);
  }, [autoPlay, game, busy, makeAiMove]);

  const handleSquareClick = async (index) => {
    if (!game || game.status !== 'in_progress' || busy) return;
    setBusy(true);
    setError('');
    try {
      const data = await postJson(`/games/${game.game_id}/moves`, {
        row: Math.floor(index / 3),
        col: index % 3,
      });
      setGame(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const runBenchmark = async () => {
    setBenchmark(null);
    setBenchmarkProgress(0);
    setError('');
    setBusy(true);
    const totals = { agent1_wins: 0, agent2_wins: 0, draws: 0 };
    const batchSize = 10;
    try {
      for (let completed = 0; completed < benchmarkSize; completed += batchSize) {
        const count = Math.min(batchSize, benchmarkSize - completed);
        const result = await postJson('/benchmark', {
          difficulty_1: benchmarkAgents[0],
          difficulty_2: benchmarkAgents[1],
          num_games: count,
        });
        totals.agent1_wins += result.agent1_wins;
        totals.agent2_wins += result.agent2_wins;
        totals.draws += result.draws;
        const done = completed + count;
        setBenchmarkProgress(Math.round((done / benchmarkSize) * 100));
        setBenchmark({ ...totals, games: done });
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const board = game?.board.flat() ?? Array(9).fill('');
  const scores = game?.analysis?.scores ?? {};
  const scoreCells = Array.from({ length: 9 }, (_, index) => {
    if (board[index]) return board[index];
    return scores[index] ?? scores[String(index)] ?? '—';
  });

  return (
    <main className="game-shell">
      <header className="page-heading">
        <p className="eyebrow">ADVERSARIAL SEARCH LAB</p>
        <h1>Tic-Tac-Toe</h1>
        <p>Play, compare strategies, and watch the search in action.</p>
      </header>

      <section className="panel setup-panel">
        <label>
          Game mode
          <select value={mode} onChange={(event) => setMode(event.target.value)}>
            {MODES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
        </label>
        {mode === 'human_ai' && (
          <>
            <label>
              AI difficulty
              <select value={difficulty} onChange={(event) => setDifficulty(event.target.value)}>
                {DIFFICULTIES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <label>
              Play as
              <select value={playerSymbol} onChange={(event) => setPlayerSymbol(event.target.value)}>
                <option value="X">X</option>
                <option value="O">O</option>
              </select>
            </label>
          </>
        )}
        {mode === 'ai_vs_ai' && (
          <>
            <label>
              X difficulty
              <select value={difficulty} onChange={(event) => setDifficulty(event.target.value)}>
                {DIFFICULTIES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <label>
              O difficulty
              <select value={opponentDifficulty} onChange={(event) => setOpponentDifficulty(event.target.value)}>
                {DIFFICULTIES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
          </>
        )}
        <button className="primary-button" onClick={startGame} disabled={busy}>
          {game ? 'New Game' : 'Start Game'}
        </button>
      </section>

      {error && <p className="error-message" role="alert">{error}</p>}

      {game && (
        <section className="game-layout">
          <div className="panel play-panel">
            <div className="game-status">
              {game.status === 'draw' ? 'It’s a draw' : game.winner ? `${game.winner} wins!` : `${game.current_player} to move`}
            </div>
            <Board board={board} onSquareClick={game.mode === 'ai_vs_ai' ? () => {} : handleSquareClick} />
            {game.mode === 'ai_vs_ai' && game.status === 'in_progress' && (
              <div className="button-row">
                <button onClick={makeAiMove} disabled={busy || autoPlay}>Step</button>
                <button className="primary-button" onClick={() => setAutoPlay(!autoPlay)} disabled={busy}>
                  {autoPlay ? 'Pause' : 'Auto Play'}
                </button>
              </div>
            )}
            {game.mode === 'two_player' && <p className="helper-text">Pass the device after each turn.</p>}
          </div>

          <aside className="panel analysis-panel">
            <div className="panel-title-row">
              <div>
                <p className="eyebrow">LIVE DECISION VISUALIZER</p>
                <h2>Move scores</h2>
              </div>
              <span className="tag">{game.current_player ?? 'FINISHED'} turn</span>
            </div>
            <div className="score-grid" aria-label="Candidate move score matrix">
              {scoreCells.map((score, index) => (
                <div className={board[index] ? 'score-cell occupied' : 'score-cell'} key={index}>
                  <small>{index + 1}</small><strong>{score}</strong>
                </div>
              ))}
            </div>
            <div className="stat-row">
              <span>Search nodes</span><strong>{game.analysis?.nodes ?? 0}</strong>
            </div>
            <div className="stat-row">
              <span>Alpha-beta cutoffs</span><strong>{game.analysis?.cutoffs ?? 0}</strong>
            </div>
            <p className="helper-text">Scores are minimax values for the current position. Higher is better for the side to move.</p>
          </aside>
        </section>
      )}

      <section className="panel benchmark-panel">
        <div>
          <p className="eyebrow">SIMULATION BENCHMARK</p>
          <h2>Bot vs bot</h2>
          <p className="helper-text">Run a batch of games and watch the results update.</p>
        </div>
        <div className="benchmark-controls">
          <label>
            X bot
            <select value={benchmarkAgents[0]} onChange={(event) => setBenchmarkAgents([event.target.value, benchmarkAgents[1]])}>
              {DIFFICULTIES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
          </label>
          <label>
            O bot
            <select value={benchmarkAgents[1]} onChange={(event) => setBenchmarkAgents([benchmarkAgents[0], event.target.value])}>
              {DIFFICULTIES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
          </label>
          <label>
            Games
            <select value={benchmarkSize} onChange={(event) => setBenchmarkSize(Number(event.target.value))}>
              <option value={20}>20</option><option value={50}>50</option><option value={100}>100</option>
            </select>
          </label>
          <button className="primary-button" onClick={runBenchmark} disabled={busy}>Run Benchmark</button>
        </div>
        {benchmark && (
          <div className="benchmark-results">
            <div className="progress-track"><span style={{ width: `${benchmarkProgress}%` }} /></div>
            <p className="helper-text">{benchmarkProgress}% complete · {benchmark.games} games</p>
            <div className="result-grid">
              <div><strong>{((benchmark.agent1_wins / benchmark.games) * 100).toFixed(0)}%</strong><span>X wins ({benchmark.agent1_wins})</span></div>
              <div><strong>{((benchmark.draws / benchmark.games) * 100).toFixed(0)}%</strong><span>Draws ({benchmark.draws})</span></div>
              <div><strong>{((benchmark.agent2_wins / benchmark.games) * 100).toFixed(0)}%</strong><span>O wins ({benchmark.agent2_wins})</span></div>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
