"use client";
import { useState } from "react";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const validateEmail = (email) => {
    return /\S+@\S+\.\S+/.test(email);
  };

  const checkEmailInDatabase = async (email) => {
    return false; // placeholder for MongoDB check
  };

  const checkPasswordInDatabase = async (password) => {
    return false; // placeholder for MongoDB password check
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!validateEmail(email)) {
      setError("Invalid email format");
      return;
    }

    const emailExists = await checkEmailInDatabase(email);
    if (emailExists) {
      setError("Email already registered");
      return;
    }

    const passwordExists = await checkPasswordInDatabase(password);
    if (passwordExists) {
      setError("Password already in use, choose another");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setSuccess("Registration successful (placeholder)");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="bg-gray-800 p-8 rounded-2xl shadow-lg w-full max-w-md">
        <h2 className="text-2xl font-bold text-white mb-6 text-center">Register</h2>
        <form onSubmit={handleRegister} className="space-y-4">
          <input
            type="email"
            placeholder="Enter your email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-2 rounded-xl bg-gray-700 text-white focus:outline-none focus:ring-2 focus:ring-green-500"
          />
          <input
            type="password"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-2 rounded-xl bg-gray-700 text-white focus:outline-none focus:ring-2 focus:ring-green-500"
          />
          <input
            type="password"
            placeholder="Confirm password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full px-4 py-2 rounded-xl bg-gray-700 text-white focus:outline-none focus:ring-2 focus:ring-green-500"
          />
          {error && <p className="text-red-500 text-sm">{error}</p>}
          {success && <p className="text-green-500 text-sm">{success}</p>}
          <button
            type="submit"
            className="w-full bg-green-600 hover:bg-green-700 text-white py-2 rounded-xl transition"
          >
            Register
          </button>
        </form>
      </div>
    </div>
  );
}
