import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import { tasksApi } from "../api/services";
import { useAuth } from "../context/AuthContext";
import { PriorityBadge, StatusBadge } from "../components/Badges";
import Spinner from "../components/Spinner";
import { formatDate, formatDateTime, getErrorMessage, isOverdue } from "../utils/errors";

export default function TaskDetails() {
  const { id } = useParams();
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const [task, setTask] = useState(null);
  const home = isAdmin ? "/admin" : "/dashboard";

  useEffect(() => {
    tasksApi
      .get(id)
      .then((r) => setTask(r.data))
      .catch((e) => {
        toast.error(getErrorMessage(e, "Task not found"));
        navigate(home);
      });
  }, [id, home, navigate]);

  const toggle = async () => {
    try {
      const { data } = await tasksApi.setStatus(id, task.status === "completed" ? "pending" : "completed");
      setTask(data);
      toast.success("Status updated");
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  };

  const remove = async () => {
    if (!window.confirm("Delete this task permanently?")) return;
    try {
      await tasksApi.remove(id);
      toast.success("Task deleted");
      navigate(home);
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  };

  if (!task) return <Spinner />;

  return (
    <div className="page narrow">
      <Link to={home} className="muted">← Back</Link>
      <div className="card details">
        <div className="task-head">
          <h1>{task.title}</h1>
          <PriorityBadge value={task.priority} />
        </div>
        <p className="task-desc">{task.description || <em className="muted">No description</em>}</p>
        <dl>
          <dt>Status</dt><dd><StatusBadge value={task.status} /></dd>
          <dt>Due date</dt><dd className={isOverdue(task) ? "overdue" : ""}>{formatDate(task.due_date)}</dd>
          <dt>Created</dt><dd>{formatDateTime(task.created_at)}</dd>
          <dt>Updated</dt><dd>{formatDateTime(task.updated_at)}</dd>
          {task.owner && (<><dt>Owner</dt><dd>{task.owner.full_name} ({task.owner.email})</dd></>)}
          <dt>Task ID</dt><dd>#{task.id}</dd>
        </dl>
        <div className="task-actions">
          <button className="btn" onClick={toggle}>{task.status === "completed" ? "Mark pending" : "Mark completed"}</button>
          <Link className="btn btn-outline" to={`/tasks/${task.id}/edit`}>Edit</Link>
          <button className="btn btn-danger" onClick={remove}>Delete</button>
        </div>
      </div>
    </div>
  );
}
