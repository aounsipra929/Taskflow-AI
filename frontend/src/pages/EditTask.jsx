import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import { tasksApi } from "../api/services";
import { useAuth } from "../context/AuthContext";
import TaskForm from "../components/TaskForm";
import Spinner from "../components/Spinner";
import { getErrorMessage } from "../utils/errors";

export default function EditTask() {
  const { id } = useParams();
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const [task, setTask] = useState(null);
  const [saving, setSaving] = useState(false);
  const home = isAdmin ? "/admin" : "/dashboard";

  useEffect(() => {
    tasksApi
      .get(id)
      .then((r) => setTask(r.data))
      .catch((e) => {
        toast.error(getErrorMessage(e, "Task not found"));
        navigate(home);
      });
  }, [id, home, navigate]);

  const submit = async (payload) => {
    setSaving(true);
    try {
      await tasksApi.update(id, payload);
      toast.success("Task updated");
      navigate(`/tasks/${id}`);
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  if (!task) return <Spinner />;
  return (
    <div className="page narrow">
      <h1>Edit task</h1>
      {isAdmin && task.owner && <p className="muted">Owner: {task.owner.full_name} ({task.owner.email})</p>}
      <TaskForm initial={task} onSubmit={submit} saving={saving} submitLabel="Save changes" onCancel={() => navigate(-1)} />
    </div>
  );
}
