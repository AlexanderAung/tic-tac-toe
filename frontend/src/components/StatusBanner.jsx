export default function StatusBanner({ winner }) {
  if (winner === 'draw') return <p>It's a draw!</p>;
  if (winner) return <p>Winner: {winner}</p>;
  return <p>Your turn (X)</p>;
}