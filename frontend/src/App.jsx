import { useEffect, useState } from "react";

function App() {
  const [message, setMessage] = useState("Connecting...");
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/health")
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => setMessage(data.message))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div>
      <h1>Frontend ↔ Backend Test</h1>
      <p>{error ? `Connection failed: ${error}` : message}</p>
    </div>
  );
}

export default App;
