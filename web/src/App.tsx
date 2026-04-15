import { useEffect, useState } from "react";

function App() {
  const [health, setHealth] = useState<string>("checking...");

  useEffect(() => {
    fetch("/api/v1/health")
      .then((res) => res.json())
      .then((data) => setHealth(data.status))
      .catch(() => setHealth("unreachable"));
  }, []);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-pitch-500 mb-4">
          TransferAtlas
        </h1>
        <p className="text-lg text-gray-400">
          API status:{" "}
          <span
            className={
              health === "ok" ? "text-green-400 font-semibold" : "text-red-400"
            }
          >
            {health}
          </span>
        </p>
      </div>
    </div>
  );
}

export default App;
