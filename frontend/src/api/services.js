import api from "./client";

// Remove empty values so they are not sent as query params.
const clean = (params = {}) =>
  Object.fromEntries(Object.entries(params).filter(([, v]) => v !== "" && v != null));

export const authApi = {
  login: (email, password) =>
    api.post("/auth/login", new URLSearchParams({ username: email, password }), {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    }),
  register: (data) => api.post("/auth/register", data),
  me: () => api.get("/auth/me"),
};

export const usersApi = {
  updateProfile: (data) => api.put("/users/me", data),
};

export const tasksApi = {
  list: (params) => api.get("/tasks", { params: clean(params) }),
  get: (id) => api.get(`/tasks/${id}`),
  create: (data) => api.post("/tasks", data),
  update: (id, data) => api.put(`/tasks/${id}`, data),
  setStatus: (id, status) => api.patch(`/tasks/${id}/status`, { status }),
  remove: (id) => api.delete(`/tasks/${id}`),
};

export const adminApi = {
  stats: () => api.get("/admin/stats"),
  listUsers: (params) => api.get("/admin/users", { params: clean(params) }),
  getUser: (id) => api.get(`/admin/users/${id}`),
  setUserStatus: (id, is_active) => api.patch(`/admin/users/${id}/status`, { is_active }),
  listTasks: (params) => api.get("/admin/tasks", { params: clean(params) }),
  createTask: (data) => api.post("/admin/tasks", data),
};

// The LLM call can take a while (free models are slow), so allow a longer timeout.
const CHAT_TIMEOUT = 90000;
export const chatApi = {
  status: () => api.get("/chat/status"),
  send: (data) => api.post("/chat", data, { timeout: CHAT_TIMEOUT }),
  confirm: (actionId) => api.post(`/chat/actions/${actionId}/confirm`),
  cancel: (actionId) => api.post(`/chat/actions/${actionId}/cancel`),
};
