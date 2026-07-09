import { API_URL } from "./config";

export const sendChatMessage = async (message, token) => {
    const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message }),
    });

    if (!res.ok) {
        throw new Error(`Error sending chat message: ${res.statusText}`);
    }

    return res.json();
};
