import ChatTaskCard from "./ChatTaskCard";

const TITLES = { create_task: "Create task", update_task: "Update task", delete_task: "Delete task" };

/**
 * Shows exactly what the backend prepared (the summary is built by the server from validated data)
 * and only changes anything when the person presses Confirm.
 */
export default function ConfirmationCard({ action, onConfirm, onCancel }) {
  const { state, error } = action;
  const busy = state === "busy";
  const open = state === "idle" || busy;

  return (
    <div className={`chat-confirm ${action.destructive ? "danger" : ""}`} role="group" aria-label="Confirm action">
      <div className="chat-confirm-title">{TITLES[action.action_type] || "Action"}</div>
      <p className="chat-confirm-summary">{action.summary}</p>
      {action.task && <ChatTaskCard task={action.task} compact />}
      {action.destructive && open && <p className="field-error">This cannot be undone.</p>}
      {error && <p className="field-error" role="alert">{error}</p>}

      {open ? (
        <div className="task-actions">
          <button className={`btn btn-sm ${action.destructive ? "btn-danger" : ""}`} onClick={onConfirm} disabled={busy}>
            {busy ? "Working…" : action.destructive ? "Yes, delete" : "Confirm"}
          </button>
          <button className="btn btn-outline btn-sm" onClick={onCancel} disabled={busy}>Cancel</button>
        </div>
      ) : (
        <p className="muted">
          {state === "done" && "✅ Done"}
          {state === "cancelled" && "Cancelled"}
          {state === "failed" && "This request can no longer be applied. Ask me again if you still need it."}
        </p>
      )}
    </div>
  );
}
