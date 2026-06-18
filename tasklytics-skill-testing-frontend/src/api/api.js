import { API_URL } from "./config";

// ----------------- AUTH -------------------

export const register = async (user) => {
    const res = await fetch(`${API_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(user),
    });

    return res.json();
};

export const login = async(user) => {
    const res = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(user),
    });

    return res.json()
};


// ---------------- TASK -------------------------

export const getTasks = async (token) => {
    const res = await fetch(`${API_URL}/tasks/`, {
        headers: {
            Authorization: `Bearer ${token}`,
        },
    });

    return res.json();
};


export const createTask = async (task, token) => {
    const res = await fetch(`${API_URL}/tasks/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(task),
    });

    return res.json()
}

export const updateTask = async (id, task, token) => {
    const res = await fetch(`${API_URL}/tasks/${id}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(task),
    });

    return res.json();
};

export const deleteTask = async (taskId, token) => {
    const res = await fetch(`${API_URL}/tasks/${taskId}`, {
        method: "DELETE",
        headers: {
            Authorization: `Bearer ${token}` ,
        },
    });

    return res.json();
};