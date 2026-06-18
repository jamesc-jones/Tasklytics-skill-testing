import { useState} from "react";
import { createTask } from "../api/api";

export default function CreateTask({ token, setTasks }) {
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [priority, setPriority] = useState("medium");

    const handleCreate = async () => {
        if (!title.trim()) return;

        const task = {
            title,
            description,
            priority,
        };

        const res = await createTask(task, token);

        if (res.data){
            setTasks((prev) => [...prev, res.data]);

            setTitle("");
            setDescription("");
            setPriority("medium")
        }
    };

    return (
        <div>
            <h3>Create Task</h3>

            <input 
                placeholder="Title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
            />
            <textarea 
                placeholder="Description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
            />

            <select 
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
            >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>   
            </select>

            <button onClick={handleCreate}>Add Task</button>
        </div>
    );
}