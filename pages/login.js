export default function Login() {
    const fakeDatabase = [
        { username: "john@example.com", password: "1234" },
        { username: "alice", password: "password123" }
    ];

    function handleLogin(event) {
        event.preventDefault();

        const username = event.target.username.value.trim();
        const password = event.target.password.value.trim();

        const userFound = fakeDatabase.find(
            user => user.username === username && user.password === password
        );

        const messageElement = document.getElementById("message");
        if (userFound) {
            messageElement.textContent = "✅ Login successful!";
            messageElement.style.color = "green";
        } else {
            messageElement.textContent = "❌ Invalid username or password.";
            messageElement.style.color = "red";
        }
    }

    return (
        <div className="flex flex-col items-center justify-center min-h-screen text-center bg-gray-200">
            <h1 className="text-4xl font-bold text-green-700 mb-6">Login</h1>
            <form onSubmit={handleLogin} className="flex flex-col gap-4 w-64">
                <input 
                    type="text" 
                    name="username" 
                    placeholder="Email or Username"
                    className="border border-gray-300 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-green-400"
                    required
                />
                <input 
                    type="password" 
                    name="password" 
                    placeholder="Password"
                    className="border border-gray-300 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-green-400"
                    required
                />
                <button 
                    type="submit"
                    className="bg-green-500 text-white rounded-lg p-2 hover:bg-green-600 transition shadow-md"
                >
                    Login
                </button>
            </form>
            <p id="message" className="mt-4 text-sm"></p>
        </div>
    );
}