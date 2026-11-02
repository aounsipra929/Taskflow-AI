import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import { adminApi } from "../api/services";
import TaskBrowser from "../components/TaskBrowser";
import Spinner from "../components/Spinner";
import { getErrorMessage } from "../utils/errors";

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    const load = () => adminApi.stats().then((r) => setStats(r.data)).catch((e) => toast.error(getErrorMessage(e)));
    load();
    // Refresh the numbers when the Chatbot Assistant creates / changes / deletes a task.
    window.addEventListener("tasks:changed", load);
    return () => window.removeEventListener("tasks:changed", load);
  }, []);

  const cards = stats && [
    ["Total users", stats.total_users, "users"],
    ["Total tasks", stats.total_tasks, "tasks"],
    ["Completed", stats.completed_tasks, "done"],
    ["Pending", stats.pending_tasks, "pending"],
  ];

  return (
    <div className="page">
      <div className="page-head">
        <h1>Admin Dashboard</h1>
        <div className="row">
          <Link to="/admin/users" className="btn btn-outline">Manage users</Link>
          <Link to="/tasks/new" className="btn">+ New task</Link>
        </div>
      </div>
      {!stats ? (
        <Spinner />
      ) : (
        <div className="stats">
          {cards.map(([label, value, cls]) => (
            <div key={label} className={`card stat stat-${cls}`}>
              <span className="stat-value">{value}</span>
              <span className="muted">{label}</span>
            </div>
          ))}
        </div>
      )}
      <h2>All tasks</h2>
      <TaskBrowser fetcher={adminApi.listTasks} showOwner />
    </div>
  );
}
