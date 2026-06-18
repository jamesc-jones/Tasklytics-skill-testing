import { API_URL } from "./config";

export const getAnalytics = async (token) => {
    const res = await fetch(`${API_URL}/tasks/analytics`, {
        headers: {
            Authorization: `Bearer ${token}`
        },
    });

    return res.json();
}