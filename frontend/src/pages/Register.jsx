import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { useAuth } from "../context/AuthContext";
import { getErrorMessage } from "../utils/errors";

export default function Register() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", password: "", confirm: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const set = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    if (form.password.length < 8 || !/[A-Za-z]/.test(form.password) || !/\d/.test(form.password)) {
      return setError("Password needs 8+ characters with at least one letter and one number");
    }
    if (form.password !== form.confirm) return setError("Passwords do not match");
    setError("");
    setSubmitting(true);
    try {
      await register({ full_name: form.full_name.trim(), email: form.email.trim(), password: form.password });
      toast.success("Account created! Please sign in.");
      navigate("/login");
    } catch (err) {
      toast.error(getErrorMessage(err, "Registration failed"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <form className="card auth-card form" onSubmit={submit}>
        <h1>Create account</h1>
        <label>Full name <input name="full_name" required minLength={2} value={form.full_name} onChange={set} /></label>
        <label>Email <input name="email" type="email" required value={form.email} onChange={set} /></label>
        <label>Password <input name="password" type="password" required value={form.password} onChange={set} autoComplete="new-password" /></label>
        <label>Confirm password <input name="confirm" type="password" required value={form.confirm} onChange={set} autoComplete="new-password" /></label>
        {error && <p className="field-error">{error}</p>}
        <button className="btn" disabled={submitting}>{submitting ? "Creating…" : "Register"}</button>
        <p className="muted">Already registered? <Link to="/login">Sign in</Link></p>
      </form>
    </div>
  );
}
