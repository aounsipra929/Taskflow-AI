import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { useAuth } from "../context/AuthContext";
import { getErrorMessage } from "../utils/errors";

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "" });
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to={user.role === "admin" ? "/admin" : "/dashboard"} replace />;

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const u = await login(form.email.trim(), form.password);
      toast.success(`Welcome back, ${u.full_name}!`);
      navigate(location.state?.from?.pathname || (u.role === "admin" ? "/admin" : "/dashboard"), { replace: true });
    } catch (err) {
      toast.error(getErrorMessage(err, "Login failed"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <form className="card auth-card form" onSubmit={submit}>
        <h1>Sign in</h1>
        <label>Email
          <input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} autoComplete="email" />
        </label>
        <label>Password
          <input type="password" required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} autoComplete="current-password" />
        </label>
        <button className="btn" disabled={submitting}>{submitting ? "Signing in…" : "Sign in"}</button>
        <p className="muted">No account? <Link to="/register">Register</Link></p>
      </form>
    </div>
  );
}
