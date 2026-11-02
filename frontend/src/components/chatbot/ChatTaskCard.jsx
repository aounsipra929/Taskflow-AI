import { useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import { tasksApi } from "../../api/services";
import { formatDate, getErrorMessage, isOverdue } from "../../utils/errors";
import { PriorityBadge, StatusBadge } from "../Badges";

/**
 * A task shown inside the chat. Cards come straight from the database (via the backend),
 * never from text the model wrote. `compact` hides the buttons (used inside confirmations).
 */
export default function ChatTaskCard({ task: initial, compact = false, onChanged }) {
  const [task, setTask] = useState(initial);
  const [busy, setBusy] = useState(false);
  const completed = task.status === "completed";
  const overdue = isOverdue(task);
  const saved = task.id > 0; // id 0 = a task that does not exist yet (preview of a new task)

  const toggle = async () => {
    setBusy(true);
    try {
      const { data } = await tasksApi.setStatus(task.id, completed ? "pending" : "completed");
      setTask((t) => ({ ...t, status: data.status }));
      toast.success("Task updated");
      window.dispatchEvent(new Event("tasks:changed"));
      onChanged?.();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`chat-task ${completed ? "done" : ""}`}>
      <div className="task-head">
        {saved && !compact ? (
          <Link to={`/tasks/${task.id}`} className="task-title">{task.title}</Link>
        ) : (
          <span className="task-title">{task.title}</span>
        )}
        <PriorityBadge value={task.priority} />
      </div>
      {task.description && <p className="task-desc">{task.description}</p>}
      <div className="task-meta">
        <StatusBadge value={task.status} />
        <span className={overdue ? "overdue" : ""}>
          Due: {formatDate(task.due_date ? `${task.due_date}T00:00:00` : null)}
          {overdue && " (overdue)"}
        </span>
        {task.owner_name && <span>👤 {task.owner_name}</span>}
      </div>
      {task.reason && <div className="chat-reason">💡 {task.reason}</div>}
      {saved && !compact && (
        <div className="task-actions">
          <button className="btn btn-sm" onClick={toggle} disabled={busy}>
            {completed ? "Mark pending" : "Mark done"}
          </button>
          <Link className="btn btn-outline btn-sm" to={`/tasks/${task.id}`}>Open</Link>
          <Link className="btn btn-outline btn-sm" to={`/tasks/${task.id}/edit`}>Edit</Link>
        </div>
      )}
    </div>
  );
}
