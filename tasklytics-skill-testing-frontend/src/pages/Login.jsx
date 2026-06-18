import { useState, useContext } from "react";
import { Link, useNavigate } from "react-router-dom";
import { login } from "../api/api";
import { AuthContext } from "../context/AuthContext";


export default function Login() {
    const navigate = useNavigate();

    const { loginUser } = useContext(AuthContext);

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");

    const handleLogin = async () => {
        const data = await login({ email, password });

        if (data.access_token) {
            loginUser(data.access_token);
            navigate("/dashboard");
        } else {
            alert("Login Failed")
        }
    };

    return (
        <div className="notepad">
            <h2>Login</h2>

            <input placeholder="email" onChange={(e) => setEmail(e.target.value)} />

            <input type="password"
            placeholder="password"
            onChange={(e) => setPassword(e.target.value)}
             />

             <button onClick={handleLogin}>Login</button>

        {/* Link to registration page for users who don't have an account */}
        <p>
            Don't have an account?{" "}
            <Link to="/register">Register here</Link>
        </p>
        </div>
    );
}