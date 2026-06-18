import { API_URL } from "./config";

export const getInsights = async (tasks, token) => {
    const res = await fetch(`${API_URL}/ai/task-insights`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ tasks }),
    });

    const data = await res.json();
    return data.insight;
};