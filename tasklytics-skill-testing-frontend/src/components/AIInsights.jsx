import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { getInsights } from "../api/ai";

export default function AIInsights({ tasks, token }) {
    const [insight, setInsight] = useState("");
    const [loading, setLoading] = useState(false);

    const handleClick = async () => {
        setLoading(true);
        setInsight("Generating analysis...");

        try{

            // ENRICH DATA
            const enrichedTasks = tasks.map((t) => ({
                title: t.title,
                completed: t.completed,
                priority: t.priority || "medium",
                due_date: t.due_date || null
            }));

            const result = await getInsights(enrichedTasks, token);

            setInsight(result ?? "No insights returned.")
        } catch (err) {
            console.error(err);
            setInsight("Error generating insights.");
        }

        setLoading(false);
    };

    return(
        <div style={{ marginTop: 20 }}>
            <h3>AI Assistant</h3>

            <button onClick={handleClick} disabled={loading}>
                {loading ? "Analyzing..." : "Get AI Insights"}
            </button>

            {insight.trim() && (
                <div 
                    style={{
                        marginTop: 15,
                        padding: 15,
                        border: "1px solid #ccc",
                        maxHeight: 300,
                        overflow: "auto"
                    }}
                >
                    <ReactMarkdown>{insight}</ReactMarkdown>
                </div>
            )}
    </div>
    );
}