import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";

import { API_URL } from "../api/config";

export default function Register() {
    const navigate = useNavigate();

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");

    const handleRegister = async () => {

        if (password !== confirmPassword) {
            alert("Passwords do not match. Please try again.");
            return;
        }

        if (!email || !password || !confirmPassword) {
            alert("Please fill in all fields.");
            return;
        }


        try {
            const res = await fetch(`${API_URL}/auth/register`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ 
                    email: email.trim().toLowerCase(), 
                    password: password.trim(),
                    confirm_password: confirmPassword.trim()
                 }),
            });

            const data = await res.json();

            if (res.ok){
                alert("User created successfully!");
                navigate("/login");
            } else {
                alert(data.detail || "Registration failed. Please try again.");
            }
        } catch (err) {
            alert("Server error. Please try again later.");
    }
};

return (
    <div className="notepad">
        <h2>Register</h2>

        <input placeholder="email"
        onChange={(e) => setEmail(e.target.value)}
        />

        <input 
            type="password"
            placeholder="password"
            onChange={(e) => setPassword(e.target.value)}
        />

        <input
            type="password"
            placeholder="confirm password"
            onChange={(e) => setConfirmPassword(e.target.value)} 
        />

        <button onClick={handleRegister}>
            Register
        </button>     

        {/* Link to login page for users who already have an account */}
        <p>
            Already have an account?{" "}
            <Link to="/login">Login here</Link>
        </p>
    </div>
    );
}