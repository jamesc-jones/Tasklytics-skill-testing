import { useEffect, useState, useContext } from "react";
import { AuthContext } from "../context/AuthContext";
import { getTasks } from "../api/api";

import CreateTask from "../components/CreateTask";
import TaskList from "../components/TaskList";
import Analytics from "../components/Analytics";
import AIInsights from "../components/AIInsights";

export default function Dashboard() {
    const { token } = useContext(AuthContext);

    const [tasks, setTasks] = useState([]);

    // 🔍 DEBUG: runs ONLY when token changes
    useEffect(() => {
        console.log("TOKEN UPDATED:", token);
    }, [token]);

    // Added to test subagent one last time
    // LOAD TASKS
    useEffect(() => {

        console.log("USEEFFECT TOKEN:", token)

        if (!token) return;

        getTasks(token)
        .then((data) => {
            console.log("API RESPONSE", data);
            setTasks(data.data);
        })
        .catch((err) => console.error(err));
    }, [token]);

    return(
        <div className="notepad">

            {/* CREATE */}
            <CreateTask setTasks={setTasks} token={token} />

            {/* ANALYTICS */}
            <Analytics tasks={tasks} />

            {/* AI */}
            <AIInsights tasks={tasks} token={token}/>


            {/* TASK LIST */}
            <TaskList tasks={tasks} setTasks={setTasks} token={token} />

        </div>
    )
}  