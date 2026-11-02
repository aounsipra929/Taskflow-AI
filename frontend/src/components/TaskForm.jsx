import { useState } from "react";

const empty = { title: "", description: "", priority: "medium", status: "pending", due_date: "" };

/**
 * Shared create/edit form. `users` (optional) renders an owner selector for admins.
 */
export default function TaskForm({ initial, onSubmit, submitLabel = "Save", saving, users, onCancel }) {
  const [form, setForm] = useState({ ...empty, ...initial, due_date: initial?.due_date || "", description: initial?.description || "" });
  const [userId, setUserId] = useState(users?.[0]?.id ?? "");
  const [error, setError] = useState("");

  const set = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const handle = (e) => {
    e.preventDefault();
    if (!form.title.trim()) return setError("Title is required");
    setError("");
    const payload = {
      title: form.title.trim(),
      description: form.description.trim() || null,
      priority: form.priority,
      status: form.status,
      due_date: form.due_date || null,
    };
    if (users) payload.user_id = Number(userId);
    onSubmit(payload);
  };

  return (
    <form className="card form" onSubmit={handle}>
      {users && (
        <label>
          Assign to user
          <select value={userId} onChange={(e) => setUserId(e.target.value)} required>
            {users.map((u) => (
              <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>
            ))}
          </select>
        </label>
      )}
      <label>
        Title *
        <input name="title" value={form.title} onChange={set} maxLength={200} placeholder="What needs to be done?" />
      </label>
      <label>
        Description
        <textarea name="description" rows={4} value={form.description} onChange={set} maxLength={5000} />
      </label>
      <div className="grid-3">
        <label>
          Priority
          <select name="priority" value={form.priority} onChange={set}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </label>
        <label>
          Status
          <select name="status" value={form.status} onChange={set}>
            <option value="pending">Pending</option>
            <option value="completed">Completed</option>
          </select>
        </label>
        <label>
          Due date
          <input type="date" name="due_date" value={form.due_date} onChange={set} />
        </label>
      </div>
      {error && <p className="field-error">{error}</p>}
      <div className="form-actions">
        {onCancel && (
          <button type="button" className="btn btn-outline" onClick={onCancel}>Cancel</button>
        )}
        <button className="btn" disabled={saving}>{saving ? "Saving…" : submitLabel}</button>
      </div>
    </form>
  );
}
