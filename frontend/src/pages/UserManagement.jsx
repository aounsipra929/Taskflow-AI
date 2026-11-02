import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import { adminApi } from "../api/services";
import { useAuth } from "../context/AuthContext";
import Pagination from "../components/Pagination";
import Spinner from "../components/Spinner";
import { formatDate, getErrorMessage } from "../utils/errors";

export default function UserManagement() {
  const { user: me } = useAuth();
  const [data, setData] = useState({ items: [], total: 0, pages: 1 });
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [role, setRole] = useState("");
  const [active, setActive] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const t = setTimeout(() => { setQ(search); setPage(1); }, 400);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    adminApi
      .listUsers({ q, role, is_active: active, page, page_size: 10 })
      .then((r) => !cancelled && setData(r.data))
      .catch((e) => !cancelled && toast.error(getErrorMessage(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [q, role, active, page, reloadKey]);

  const toggle = async (u) => {
    try {
      await adminApi.setUserStatus(u.id, !u.is_active);
      toast.success(`User ${u.is_active ? "deactivated" : "activated"}`);
      setReloadKey((k) => k + 1);
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  };

  return (
    <div className="page">
      <div className="page-head"><h1>User Management</h1></div>
      <div className="card filters">
        <input className="search" type="search" placeholder="Search name or email…" value={search} onChange={(e) => setSearch(e.target.value)} />
        <select value={role} onChange={(e) => { setRole(e.target.value); setPage(1); }}>
          <option value="">All roles</option>
          <option value="admin">Admin</option>
          <option value="user">User</option>
        </select>
        <select value={active} onChange={(e) => { setActive(e.target.value); setPage(1); }}>
          <option value="">Any status</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </select>
      </div>

      {loading ? (
        <Spinner />
      ) : (
        <div className="card table-wrap">
          <table>
            <thead>
              <tr><th>Name</th><th>Email</th><th>Role</th><th>Tasks</th><th>Joined</th><th>Status</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {data.items.map((u) => (
                <tr key={u.id}>
                  <td>{u.full_name}</td>
                  <td>{u.email}</td>
                  <td><span className={`badge role-${u.role}`}>{u.role}</span></td>
                  <td>{u.task_count}</td>
                  <td>{formatDate(u.created_at)}</td>
                  <td><span className={`badge ${u.is_active ? "status-completed" : "prio-high"}`}>{u.is_active ? "active" : "inactive"}</span></td>
                  <td className="row">
                    <Link className="btn btn-outline btn-sm" to={`/admin/users/${u.id}/tasks`}>Tasks</Link>
                    <button className={`btn btn-sm ${u.is_active ? "btn-danger" : ""}`} disabled={u.id === me.id} onClick={() => toggle(u)}>
                      {u.is_active ? "Deactivate" : "Activate"}
                    </button>
                  </td>
                </tr>
              ))}
              {data.items.length === 0 && <tr><td colSpan={7} className="empty">No users found.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
      <Pagination page={page} pages={data.pages} total={data.total} onChange={setPage} />
    </div>
  );
}
