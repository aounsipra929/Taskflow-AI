import { useState } from "react";
import toast from "react-hot-toast";
import { usersApi } from "../api/services";
import { useAuth } from "../context/AuthContext";
import { formatDateTime, getErrorMessage } from "../utils/errors";

export default function Profile() {
  const { user, setUser } = useAuth();
  const [name, setName] = useState(user.full_name);
  const [pw, setPw] = useState({ current_password: "", password: "", confirm: "" });
  const [saving, setSaving] = useState(false);

  const saveName = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const { data } = await usersApi.updateProfile({ full_name: name });
      setUser(data);
      toast.success("Profile updated");
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const savePassword = async (e) => {
    e.preventDefault();
    if (pw.password !== pw.confirm) return toast.error("New passwords do not match");
    setSaving(true);
    try {
      await usersApi.updateProfile({ current_password: pw.current_password, password: pw.password });
      toast.success("Password changed");
      setPw({ current_password: "", password: "", confirm: "" });
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page narrow">
      <h1>Profile</h1>
      <div className="card">
        <p><strong>Email:</strong> {user.email}</p>
        <p><strong>Role:</strong> <span className={`badge role-${user.role}`}>{user.role}</span></p>
        <p><strong>Member since:</strong> {formatDateTime(user.created_at)}</p>
      </div>

      <form className="card form" onSubmit={saveName}>
        <h2>Edit details</h2>
        <label>Full name <input value={name} minLength={2} required onChange={(e) => setName(e.target.value)} /></label>
        <button className="btn" disabled={saving}>Save</button>
      </form>

      <form className="card form" onSubmit={savePassword}>
        <h2>Change password</h2>
        <label>Current password <input type="password" required value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} /></label>
        <label>New password <input type="password" required minLength={8} value={pw.password} onChange={(e) => setPw({ ...pw, password: e.target.value })} /></label>
        <label>Confirm new password <input type="password" required value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} /></label>
        <button className="btn" disabled={saving}>Change password</button>
      </form>
    </div>
  );
}
