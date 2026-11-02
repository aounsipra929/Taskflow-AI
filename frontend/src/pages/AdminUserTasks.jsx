import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { adminApi } from "../api/services";
import TaskBrowser from "../components/TaskBrowser";
import Spinner from "../components/Spinner";

export default function AdminUserTasks() {
  const { id } = useParams();
  const [owner, setOwner] = useState(null);

  useEffect(() => {
    adminApi.getUser(id).then((r) => setOwner(r.data)).catch(() => setOwner(false));
  }, [id]);

  if (owner === null) return <Spinner />;
  if (owner === false) return <div className="page"><div className="card empty">User not found.</div></div>;

  return (
    <div className="page">
      <Link to="/admin/users" className="muted">← Back to users</Link>
      <div className="page-head">
        <div>
          <h1>{owner.full_name}'s tasks</h1>
          <p className="muted">{owner.email} · {owner.is_active ? "active" : "inactive"}</p>
        </div>
      </div>
      <TaskBrowser fetcher={adminApi.listTasks} extraParams={{ user_id: id }} showOwner />
    </div>
  );
}
