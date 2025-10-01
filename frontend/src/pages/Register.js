import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import logo from "../assets/logo.png"; // Path to your logo

export default function Register() {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    // For now, navigate to login after registration
    navigate("/login");
  };

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      minHeight: "100vh",
      backgroundColor: "#f7f9fc",
      fontFamily: "Arial, sans-serif"
    }}>
      {/* Logo */}
      <div style={{ 
        marginBottom: "30px",
        backgroundColor: "#f7f9fc",
        borderRadius: "20px",
        padding: "20px"
      }}>
        <img 
          src={logo} 
          alt="MedLink Logo" 
          width="200" 
          style={{ opacity: 0.95 }} 
        />
      </div>

      {/* Register card */}
      <form onSubmit={handleSubmit} style={{
        display: "flex",
        flexDirection: "column",
        width: "350px",
        padding: "30px",
        backgroundColor: "#fff",
        borderRadius: "12px",
        boxShadow: "0 4px 10px rgba(0,0,0,0.1)"
      }}>
        <h2 style={{ marginBottom: "10px", color: "#2c3e50", textAlign: "center" }}>Register</h2>
        <p style={{ 
          textAlign: "center", 
          color: "#7f8c8d", 
          marginBottom: "20px", 
          fontSize: "14px"
        }}>
          Create your account to get started.
        </p>

        <input
          type="text"
          placeholder="First Name"
          value={firstName}
          onChange={(e) => setFirstName(e.target.value)}
          required
          style={{
            marginBottom: "15px",
            padding: "12px",
            borderRadius: "6px",
            border: "1px solid #ccc",
            fontSize: "16px"
          }}
        />
        <input
          type="text"
          placeholder="Last Name"
          value={lastName}
          onChange={(e) => setLastName(e.target.value)}
          required
          style={{
            marginBottom: "15px",
            padding: "12px",
            borderRadius: "6px",
            border: "1px solid #ccc",
            fontSize: "16px"
          }}
        />
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          style={{
            marginBottom: "15px",
            padding: "12px",
            borderRadius: "6px",
            border: "1px solid #ccc",
            fontSize: "16px"
          }}
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          style={{
            marginBottom: "15px",
            padding: "12px",
            borderRadius: "6px",
            border: "1px solid #ccc",
            fontSize: "16px"
          }}
        />
        <input
          type="password"
          placeholder="Confirm Password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
          style={{
            marginBottom: "20px",
            padding: "12px",
            borderRadius: "6px",
            border: "1px solid #ccc",
            fontSize: "16px"
          }}
        />

        <button type="submit" style={{
          padding: "12px",
          borderRadius: "6px",
          border: "none",
          backgroundColor: "#E53935",
          color: "#fff",
          fontWeight: "bold",
          fontSize: "16px",
          cursor: "pointer",
          marginBottom: "10px"
        }}>
          Create
        </button>

        <p style={{ textAlign: "center", color: "#555", marginTop: "10px" }}>
          Already have an account? <Link to="/login" style={{ color: "#E53935" }}>Login</Link>
        </p>
      </form>
    </div>
  );
}
