import { useState } from "react";
import Link from "next/link";

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

      <button className="mt-4 px-5 py-2 bg-blue-500 text-white font-medium rounded-lg shadow hover:bg-blue-600 transition">
        <Link href="/login">login page</Link>
      </button>

      <button className="mt-4 px-5 py-2 bg-purple-500 text-white font-medium rounded-lg shadow hover:bg-purple-600 transition">
        <Link href="/register">register page</Link>
      </button>
    </div>
  );
}
