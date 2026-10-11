import Square from './Square';

export default function Board({ board, onSquareClick }) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(3, 80px)',
      gap: 4,
      width: 'fit-content',
      marginInline: 'auto',
    }}>
      {board.map((value, i) => (
        <Square key={i} value={value} onClick={() => onSquareClick(i)} />
      ))}
    </div>
  );
}
