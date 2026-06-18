import { createContext, useState, useEffect } from "react";

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {

    const [token, setToken] = useState(() => {
        return localStorage.getItem("token");
    });


    /* Load token on refresh
     useEffect(() => {
       const stored = localStorage.getItem("token");
        if (stored) {
            setToken(stored);
        }
    }, []);*/

    const loginUser = (newToken) => {
        setToken(newToken);
        localStorage.setItem("token", newToken);
    };

    const logoutUser = () => {
        setToken(null);
        localStorage.removeItem("token");
    };

    return (
        <AuthContext.Provider value={{ token, loginUser, logoutUser }}>
            {children}
        </AuthContext.Provider>
    );
};