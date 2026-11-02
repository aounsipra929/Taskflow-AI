import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import { tasksApi } from "../api/services";
import { formatDate, getErrorMessage, isOverdue } from "../utils/errors";
import { PriorityBadge, StatusBadge } from "./Badges";
import Pagination from "./Pagination";
import Spinner from "./Spinner";

const DEFAULT_FILTERS = { q: "", status: "", priority: "", due_from: "", due_to: "", sort_by: "created_at", order: "desc" };

/**
 * Task list with search, filters, sorting, pagination and row actions.
 * `fetcher(params)` returns an axios promise (user or admin endpoint).
 */
export default function TaskBrowser({ fetcher, extraParams = {}, showOwner = false }) {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ items: [], total: 0, pages: 1 });
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);
  const extraKey = JSON.stringify(extraParams);

  // Debounce the search box.
  useEffect(() => {
    const t = setTimeout(() => {
      setFilters((f) => (f.q === search ? f : { ...f, q: search }));
      setPage(1);
    }, 400);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetcher({ ...filters, ...JSON.parse(extraKey), page, page_size: 8 })
      .then((res) => !cancelled && setData(res.data))
      .catch((err) => !cancelled && toast.error(getErrorMessage(err, "Failed to load tasks")))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, page, extraKey, reloadKey]);

  const change = (e) => {
    setFilters((f) => ({ ...f, [e.target.name]: e.target.value }));
    setPage(1);
  };
  const reset = () => {
    setSearch("");
    setFilters(DEFAULT_FILTERS);
    setPage(1);
  };
  const reload = useCallback(() => setReloadKey((k) => k + 1), []);

  // The Chatbot Assistant announces task changes so this list stays in sync.
  useEffect(() => {
    window.addEventListener("tasks:changed", reload);
    return () => window.removeEventListener("tasks:changed", reload);
  }, [reload]);

  const toggleStatus = async (task) => {
    try {
      await tasksApi.setStatus(task.id, task.status === "completed" ? "pending" : "completed");
      toast.success("Task updated");
      reload();
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  const remove = async (task) => {
    if (!window.confirm(`Delete "${task.title}"?`)) return;
    try {
      await tasksApi.remove(task.id);
      toast.success("Task deleted");
      // Step back a page if we just removed the last item on it.
      if (data.items.length === 1 && page > 1) setPage(page - 1);
      else reload();
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  return (
    <div>
      <div className="card filters">
        <input
          className="search"
          type="search"
          placeholder="Search title or description…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select name="status" value={filters.status} onChange={change}>
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="completed">Completed</option>
        </select>
        <select name="priority" value={filters.priority} onChange={change}>
          <option value="">All priorities</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </select>
        <label className="inline">Due from <input type="date" name="due_from" value={filters.due_from} onChange={change} /></label>
        <label className="inline">Due to <input type="date" name="due_to" value={filters.due_to} onChange={change} /></label>
        <select name="sort_by" value={filters.sort_by} onChange={change}>
          <option value="created_at">Sort: Created</option>
          <option value="due_date">Sort: Due date</option>
          <option value="priority">Sort: Priority</option>
        </select>
        <select name="order" value={filters.order} onChange={change}>
          <option value="desc">Descending</option>
          <option value="asc">Ascending</option>
        </select>
        <button className="btn btn-outline btn-sm" onClick={reset}>Reset</button>
      </div>

      {loading ? (
        <Spinner />
      ) : data.items.length === 0 ? (
        <div className="card empty">No tasks found.</div>
      ) : (
        <div className="task-grid">
          {data.items.map((t) => (
            <div key={t.id} className={`card task ${t.status === "completed" ? "done" : ""}`}>
              <div className="task-head">
                <Link to={`/tasks/${t.id}`} className="task-title">{t.title}</Link>
                <PriorityBadge value={t.priority} />
              </div>
              {t.description && <p className="task-desc">{t.description}</p>}
              <div className="task-meta">
                <StatusBadge value={t.status} />
                <span className={isOverdue(t) ? "overdue" : ""}>
                  Due: {formatDate(t.due_date)}{isOverdue(t) && " (overdue)"}
                </span>
                {showOwner && t.owner && <span className="owner">👤 {t.owner.full_name}</span>}
              </div>
              <div className="task-actions">
                <button className="btn btn-sm" onClick={() => toggleStatus(t)}>
                  {t.status === "completed" ? "Mark pending" : "Mark done"}
                </button>
                <Link className="btn btn-outline btn-sm" to={`/tasks/${t.id}/edit`}>Edit</Link>
                <button className="btn btn-danger btn-sm" onClick={() => remove(t)}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}
      <Pagination page={page} pages={data.pages} total={data.total} onChange={setPage} />
    </div>
  );
}
