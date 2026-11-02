import { useEffect, useRef, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useChat } from "../../context/ChatContext";
import ChatTaskCard from "./ChatTaskCard";
import ConfirmationCard from "./ConfirmationCard";

const PROMPTS = {
  user: [
    "Show my pending tasks",
    "Which tasks are most urgent?",
    "Suggest what I should work on next",
    "Create a task to finish my assignment tomorrow",
  ],
  admin: [
    "Show task statistics",
    "Show all overdue tasks",
    "Which tasks are most urgent?",
    "Suggest what I should work on next",
  ],
};

const STAT_LABELS = [
  ["total_tasks", "Total"],
  ["pending_tasks", "Pending"],
  ["completed_tasks", "Completed"],
  ["overdue_tasks", "Overdue"],
  ["high_priority_pending", "High priority"],
  ["due_today", "Due today"],
  ["due_next_7_days", "Next 7 days"],
  ["total_users", "Users"],
  ["active_users", "Active users"],
];

function Stats({ stats }) {
  return (
    <div className="chat-stats">
      {STAT_LABELS.filter(([key]) => stats[key] !== undefined).map(([key, label]) => (
        <div key={key} className="chat-stat">
          <strong>{stats[key]}</strong>
          <span>{label}</span>
        </div>
      ))}
    </div>
  );
}

function Typing() {
  return (
    <div className="chat-msg assistant" role="status" aria-label="The assistant is typing">
      <div className="chat-bubble typing"><span /><span /><span /></div>
    </div>
  );
}

export default function Chatbot() {
  const { user, isAdmin } = useAuth();
  const { open, setOpen, messages, sending, enabled, send, retry, confirm, cancel, reset } = useChat();
  const [draft, setDraft] = useState("");
  const endRef = useRef(null);
  const inputRef = useRef(null);

  // Keep the newest message in view and focus the box when the window opens.
  useEffect(() => {
    endRef.current?.scrollIntoView?.({ block: "end" });
  }, [messages, sending, open]);
  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  if (!user) return null; // only for signed-in Admin and User pages

  const submit = (text) => {
    if (!text.trim() || sending || enabled === false) return;
    setDraft("");
    send(text);
  };
  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit(draft);
    }
  };

  const firstName = (user.full_name || "").split(" ")[0] || "there";
  const prompts = isAdmin ? PROMPTS.admin : PROMPTS.user;

  if (!open) {
    return (
      <button className="chatbot-fab" onClick={() => setOpen(true)} aria-label="Open Chatbot Assistant" title="Chatbot Assistant">
        <span aria-hidden="true">💬</span>
      </button>
    );
  }

  return (
    <section
      className="chatbot-window"
      role="dialog"
      aria-label="Chatbot Assistant"
      onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
    >
      <header className="chatbot-header">
        <div>
          <strong>Chatbot Assistant</strong>
          <div className="chatbot-sub">{isAdmin ? "Admin – all users' tasks" : "Your tasks"}</div>
        </div>
        <div className="row">
          {messages.length > 0 && (
            <button className="chatbot-icon-btn" onClick={reset} aria-label="Start a new chat" title="New chat">↺</button>
          )}
          <button className="chatbot-icon-btn" onClick={() => setOpen(false)} aria-label="Close chat">✕</button>
        </div>
      </header>

      <div className="chatbot-body" aria-live="polite">
        {enabled === false && (
          <div className="chat-notice" role="alert">
            The assistant is not set up yet. Ask your administrator to add <code>OPENROUTER_API_KEY</code> and{" "}
            <code>OPENROUTER_MODEL</code> to the backend <code>.env</code>. You can still manage tasks from the normal pages.
          </div>
        )}

        {messages.length === 0 && (
          <div className="chat-msg assistant">
            <div className="chat-bubble">
              Hi {firstName}! I can search your tasks, tell you what is urgent, and create, update or delete tasks
              (I always ask you to confirm first). What would you like to do?
              <div className="chat-prompts">
                {prompts.map((p) => (
                  <button key={p} className="chat-chip" onClick={() => submit(p)} disabled={sending || enabled === false}>
                    {p}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {messages.map((m) => (
          <div key={m.id} className={`chat-msg ${m.role}`}>
            <div className={`chat-bubble ${m.error ? "error" : ""}`}>
              {m.error && <span aria-hidden="true">⚠️ </span>}
              {m.content}
              {m.error && (
                <div className="task-actions">
                  <button className="btn btn-outline btn-sm" onClick={() => retry(m.id)} disabled={sending}>Try again</button>
                </div>
              )}
            </div>
            {m.stats && <Stats stats={m.stats} />}
            {m.tasks?.length > 0 && (
              <div className="chat-cards">
                {m.tasks.map((t) => <ChatTaskCard key={t.id} task={t} />)}
              </div>
            )}
            {m.pending && (
              <ConfirmationCard
                action={m.pending}
                onConfirm={() => confirm(m.id, m.pending)}
                onCancel={() => cancel(m.id, m.pending)}
              />
            )}
          </div>
        ))}

        {sending && <Typing />}
        <div ref={endRef} />
      </div>

      <form className="chatbot-input" onSubmit={(e) => { e.preventDefault(); submit(draft); }}>
        <textarea
          ref={inputRef}
          rows={1}
          value={draft}
          maxLength={2000}
          placeholder={enabled === false ? "Assistant not configured" : "Ask about your tasks…"}
          aria-label="Message"
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={enabled === false}
        />
        <button className="btn" type="submit" disabled={!draft.trim() || sending || enabled === false}>
          {sending ? "…" : "Send"}
        </button>
      </form>
    </section>
  );
}
