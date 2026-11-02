import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { adminApi, tasksApi } from "../api/services";
import { useAuth } from "../context/AuthContext";
import TaskForm from "../components/TaskForm";
import Spinner from "../components/Spinner";
import { getErrorMessage } from "../utils/errors";

export default function CreateTask() {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const [saving, setSaving] = useState(false);
  const [users, setUsers] = useState(null); // admins pick an owner
  const home = isAdmin ? "/admin" : "/dashboard";

  useEffect(() => {
    if (!isAdmin) return;
    adminApi
      .listUsers({ is_active: "true", page_size: 100 })
      .then((r) => setUsers(r.data.items))
      .catch((e) => toast.error(getErrorMessage(e)));
  }, [isAdmin]);

  const submit = async (payload) => {
    setSaving(true);
    try {
      await (isAdmin ? adminApi.createTask(payload) : tasksApi.create(payload));
      toast.success("Task created");
      navigate(home);
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  if (isAdmin && !users) return <Spinner />;

  return (
    <div className="page narrow">
      <h1>Create task</h1>
      <TaskForm users={isAdmin ? users : undefined} onSubmit={submit} saving={saving} submitLabel="Create task" onCancel={() => navigate(home)} />
    </div>
  );
}
