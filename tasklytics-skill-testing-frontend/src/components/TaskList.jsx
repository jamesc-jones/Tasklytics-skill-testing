import { useState } from "react";
import { updateTask, deleteTask } from "../api/api";
import { toast } from "react-toastify";

export default function TaskList({ tasks, setTasks, token }) {
    const [editingTask, setEditingTask] = useState(null);
    const [editTitle, setEditTitle] = useState("");
    const [editDescription, setEditDescription] = useState("");
    const [editCompleted, setEditCompleted] = useState(false);

    const handleDelete = async (id) => {
        try{
            await deleteTask(id, token);
            setTasks((prev) => prev.filter((t) => t.id !== id));
            toast.info("Task Deleted! 🗑️");

            if (editingTask?.id === id) cancelEdit();
        } catch (err) {
            toast.error("Delete failed ❌");
        }
    };

    const handleEdit = (task) => {
        setEditingTask(task);
        setEditTitle(task.title);
        setEditDescription(task.description);
        setEditCompleted(task.completed ?? false);
    };

     const handleUpdate = async () => {
    if (!editTitle.trim()) return toast.error("Title required ❌");

    try {
      await updateTask(
        editingTask.id,
        {
          title: editTitle,
          description: editDescription,
          completed: editCompleted,
        },
        token
      );

      setTasks((prev) =>
        prev.map((t) =>
          t.id === editingTask.id
            ? { ...t, title: editTitle, description: editDescription, completed: editCompleted }
            : t
        )
      );

      setEditingTask(null);
      toast.success("Updated ✏️");
    } catch {
      toast.error("Update failed ❌");
    }
  };

  const cancelEdit = () => {
    setEditingTask(null);
    setEditTitle("");
    setEditDescription("");
    setEditCompleted(false);
  };

  const toggleComplete = async (task) => {
    const newStatus = !task.completed;

    try {
      await updateTask(task.id, { ...task, completed: newStatus }, token);

      setTasks((prev) =>
        prev.map((t) =>
          t.id === task.id ? { ...t, completed: newStatus } : t
        )
      );
    } catch {
      toast.error("Toggle failed ❌");
    }
  };

  return (
  <div>
    {editingTask && (
      <div style={{ border: "1px solid #aaa", padding: 10 }}>
        <h3>Edit Task</h3>

        <input value={editTitle} onChange={(e) => setEditTitle(e.target.value)} />
        <textarea value={editDescription} onChange={(e) => setEditDescription(e.target.value)} />

        <label>
          <input
            type="checkbox"
            checked={editCompleted}
            onChange={(e) => setEditCompleted(e.target.checked)}
          />
          Completed
        </label>

        <button onClick={handleUpdate}>Save</button>
        <button onClick={cancelEdit}>Cancel</button>
      </div>
    )}

    {/* SINGLE SAFE RENDER BLOCK */}
    {!Array.isArray(tasks) || tasks.length === 0 ? (
      <p>No tasks yet</p>
    ) : (
      tasks.map((task) => (
        <div key={task.id} style={{ border: "1px solid #ccc", marginBottom: 10 }}>
          <h4 style={{ textDecoration: task.completed ? "line-through" : "none" }}>
            {task.title}
          </h4>

          <p>{task.description}</p>

          <button onClick={() => toggleComplete(task)}>
            {task.completed ? "Undo" : "Complete"}
          </button>

          <button onClick={() => handleEdit(task)}>Edit</button>
          <button onClick={() => handleDelete(task.id)}>Delete</button>
        </div>
      ))
    )}
  </div>
 );
}