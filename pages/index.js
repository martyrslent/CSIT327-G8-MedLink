import { useState } from "react";

export default function Home() {
  const [count, setCount] = useState(0);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen text-center bg-background">
      <h1 className="text-5xl font-bold text-primary">Welcome to MedLink</h1>
      <p className="text-lg mt-4 text-secondary">Hi Developers! 😎</p>

      <button
        onClick={() => setCount(count + 1)}
        className="mt-4 px-5 py-2 bg-green-500 text-white font-medium rounded-lg shadow hover:bg-green-600 transition"
      >
        Increment Count: {count}
      </button>

    </div>
  );
}
