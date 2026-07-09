import { useState } from "react";
import { sendChatMessage } from "../../api/chat";
import ChatMessages from "./ChatMessages";
import ChatInput from "./ChatInput";

export default function ChatContainer({ token }) {
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleSend = async (text) => {
        const trimmed = text.trim();
        if (!trimmed) return;

        setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
        setLoading(true);
        setError(null);

        try {
            const data = await sendChatMessage(trimmed, token);

            setMessages((prev) => [
                ...prev,
                {
                    role: "assistant",
                    content: data.response,
                    insight: data.insight ?? null,
                    priorityTasks: data.priority_tasks ?? [],
                },
            ]);
        } catch (err) {
            console.error(err);
            setError("Failed to get a response. Please try again.");
        }
          finally {  
            setLoading(false);
          }
    };

    return (
        <div style={{ marginTop: 20 }}>
            <h3>Chat</h3>

            <ChatMessages messages={messages} loading={loading} />

            {error && <p style={{ color: "red" }}>{error}</p>}

            <ChatInput onSend={handleSend} disabled={loading} />
        </div>
    );
}
