import { PieChart, Pie, Cell, Tooltip, Legend, BarChart, Bar,
         XAxis, YAxis, CartesianGrid
        } from "recharts";

export default function TaskChart({ data }) {
    if (!data) return null;

    const completed = data.completed_tasks || 0;
    const total = data.total_tasks || 0; 

    if(total === 0) return <p>No data yet</p>

    // Chart 1: Completion
    const completionData = [
        { name: "Completed", value: completed },
        { name: "Remaining", value: Math.max(total - completed, 0) }
    ];

    const COLORS = ["#4ade80", "#f97316"];

    // Chart 2: Priority Breakdown
    const priorityData = [
        { name: "High", value: data.priority_breakdown?.high || 0 },
        { name: "Medium", value: data.priority_breakdown?.medium || 0 },
        { name: "Low", value: data.priority_breakdown?.low || 0 }
    ];


    return (
        <div style={{ display: "flex", gap: "40px", flexWrap: "wrap" }}>

            {/* Pie Chart */}
            <div>
                <h4>Task Completion</h4>
                <PieChart width={300} height={300}>
                    <Pie 
                        data={completionData}
                        dataKey="value"
                        outerRadius={100}
                        label
                    >
                        {completionData.map((_, index) => (
                            <Cell key={index} fill={COLORS[index]} />
                        ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                </PieChart>
            </div>

            {/* Bar Chart */}
            <div>
                <h4>Priority Breakdown</h4>
                <BarChart width={300} height={300} data={priorityData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="value">
                        {priorityData.map((entry, index) => {
                            const colors = ["#ef4444", "#facc15", "#22c55e"];
                            return <Cell key={index} fill={colors[index]} />;
                        })}
                    </Bar>
                </BarChart>
            </div>

        </div>
    );
}        