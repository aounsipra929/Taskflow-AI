// Turn an Axios/FastAPI error into a readable message.
export function getErrorMessage(error, fallback = "Something went wrong") {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    // Pydantic validation errors
    return detail.map((d) => `${(d.loc || []).slice(1).join(".")}: ${d.msg}`).join("; ");
  }
  if (error?.code === "ERR_NETWORK") return "Cannot reach the server";
  return fallback;
}

export const formatDate = (d) => (d ? new Date(d).toLocaleDateString() : "—");
export const formatDateTime = (d) => (d ? new Date(d).toLocaleString() : "—");
export const isOverdue = (task) =>
  task.status === "pending" && task.due_date && new Date(task.due_date) < new Date(new Date().toDateString());
