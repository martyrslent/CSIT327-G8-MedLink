export default function Dashboard() {
  return (
    <div style={{ padding: "20px" }}>
      <h1>MedLink Dashboard</h1>
      <p>Welcome back! Here you can access your features.</p>

      <div style={{ display: "flex", gap: "20px", marginTop: "20px" }}>
        <div style={{ border: "1px solid #ccc", padding: "20px", borderRadius: "10px", flex: 1 }}>
          <h2>Appointments</h2>
          <p>View and manage your appointments.</p>
        </div>

        <div style={{ border: "1px solid #ccc", padding: "20px", borderRadius: "10px", flex: 1 }}>
          <h2>Messages</h2>
          <p>Check your latest conversations.</p>
        </div>

        <div style={{ border: "1px solid #ccc", padding: "20px", borderRadius: "10px", flex: 1 }}>
          <h2>Profile</h2>
          <p>Update your personal details.</p>
        </div>
      </div>
    </div>
  );
}
