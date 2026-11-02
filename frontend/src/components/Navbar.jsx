import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { user, isAdmin, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const handleLogout = () => {
    logout();
    toast.success("Logged out");
    navigate("/login");
  };

  const link = ({ isActive }) => (isActive ? "nav-link active" : "nav-link");
  const close = () => setOpen(false);

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <span className="brand">✔ TaskFlow</span>
        <button className="nav-toggle" onClick={() => setOpen((o) => !o)} aria-label="Toggle menu">
          ☰
        </button>
        <nav className={open ? "nav open" : "nav"} onClick={close}>
          {isAdmin ? (
            <>
              <NavLink to="/admin" end className={link}>Dashboard</NavLink>
              <NavLink to="/admin/users" className={link}>Users</NavLink>
              <NavLink to="/tasks/new" className={link}>New Task</NavLink>
            </>
          ) : (
            <>
              <NavLink to="/dashboard" className={link}>My Tasks</NavLink>
              <NavLink to="/tasks/new" className={link}>New Task</NavLink>
            </>
          )}
          <NavLink to="/profile" className={link}>Profile</NavLink>
          <span className="nav-user">{user?.full_name} <span className={`badge role-${user?.role}`}>{user?.role}</span></span>
          <button className="btn btn-outline btn-sm" onClick={handleLogout}>Logout</button>
        </nav>
      </div>
    </header>
  );
}
