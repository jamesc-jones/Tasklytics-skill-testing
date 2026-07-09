import ReactMarkdown from "react-markdown";

export default function ChatMessages({ messages, loading }) {
    return (
        <div
            style={{
                marginTop: 15,
                padding: 15,
                border: "1px solid #ccc",
                maxHeight: 300,
                overflow: "auto",
            }}
        >
            {messages.length === 0 && !loading && (
                <p style={{ color: "#888" }}>No messages yet. Ask something below.</p>
            )}

            {messages.map((msg, index) => (
                <div key={index} style={{ marginBottom: 12 }}>
                    <strong>{msg.role === "user" ? "You" : "Assistant"}:</strong>
                    <ReactMarkdown>{msg.content}</ReactMarkdown>

                    {msg.priorityTasks?.length > 0 && (
                        <div>
                            <em>Priority tasks:</em>
                            <ul>
                                {msg.priorityTasks.map((task, i) => (
                                    <li key={i}>{task}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {msg.insight && (
                        <div>
                            <em>Insight:</em>
                            <ReactMarkdown>{msg.insight}</ReactMarkdown>
                        </div>
                    )}
                </div>
            ))}

            {loading && <p>Thinking...</p>}
        </div>
    );
}
