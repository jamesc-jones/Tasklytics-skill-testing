import { useEffect, useState, useContext } from "react";
import { AuthContext } from "../context/AuthContext";
import { getAnalytics } from "../api/analytics";
import TaskChart from "./TaskChart";

export default function Analytics() {
    const { token } = useContext(AuthContext);
    const [data, setData] = useState(null);

    useEffect(() => {
        getAnalytics(token)
        .then((res) => setData(res.data))
        .catch((err) => console.error("Analytics fetch failed", err));
    }, [token]);

    console.log("ANALYTICS RESPOSNSE:", data)

    if (!data) return <p>Loading analytics...</p>

    return(
        <div style={{
            padding: "15px",
            border: "1px solid #ddd",
            borderRadius: "8px",
            marginBottom: "20px"
        }}>
            <h3>Productivity Overview</h3>

            {/* KPI Section */}
            <div style={{ display: "flex", gap: "30px" }}>
                <div>
                    <h4>Total Tasks</h4>
                    <p>{data.total_tasks}</p>
                </div>

                <div>
                    <h4>Completed</h4>
                    <p>{data.completed_tasks}</p>
                </div>

                <div>
                    <h4>Completion Rate</h4>
                    <p>{data.completion_rate}%</p>
                </div>
            </div>

            {/* Chart added */}
            <div style={{ marginTop: "20px" }}>
              <TaskChart data={data} /> 
            </div>
        </div>
    );
}