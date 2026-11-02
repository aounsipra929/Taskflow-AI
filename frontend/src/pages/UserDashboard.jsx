import { Link } from "react-router-dom";
import { tasksApi } from "../api/services";
import { useAuth } from "../context/AuthContext";
import TaskBrowser from "../components/TaskBrowser";

export default function UserDashboard() {
  const { user } = useAuth();
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>My Tasks</h1>
          <p className="muted">Hello, {user.full_name}. Here is everything on your plate.</p>
        </div>
        <Link to="/tasks/new" className="btn">+ New task</Link>
      </div>
      <TaskBrowser fetcher={tasksApi.list} />
    </div>
  );
}
