export default function Square({ value, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{ width: 80, height: 80, fontSize: 32 }}
    >
      {value}
    </button>
  );
}