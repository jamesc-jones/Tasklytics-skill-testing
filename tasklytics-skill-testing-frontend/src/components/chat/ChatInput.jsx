import { useState } from "react";

export default function ChatInput({ onSend, disabled }) {
    const [text, setText] = useState("");

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!text.trim()) return;

        onSend(text);
        setText("");
    };

    return (
        <form onSubmit={handleSubmit} style={{ marginTop: 10, display: "flex", gap: 8 }}>
            <input
                type="text"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Ask about your tasks..."
                disabled={disabled}
                style={{ flex: 1 }}
            />
            <button type="submit" disabled={disabled}>
                Send
            </button>
        </form>
    );
}
