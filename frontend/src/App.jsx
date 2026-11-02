import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { useAuth } from "./context/AuthContext";
import { ChatProvider } from "./context/ChatContext";
import Chatbot from "./components/chatbot/Chatbot";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import Spinner from "./components/Spinner";
import Login from "./pages/Login";
import Register from "./pages/Register";
import UserDashboard from "./pages/UserDashboard";
import AdminDashboard from "./pages/AdminDashboard";
import UserManagement from "./pages/UserManagement";
import AdminUserTasks from "./pages/AdminUserTasks";
import CreateTask from "./pages/CreateTask";
import EditTask from "./pages/EditTask";
import TaskDetails from "./pages/TaskDetails";
import Profile from "./pages/Profile";
import NotFound from "./pages/NotFound";

// Layout shown to every authenticated page.
const AppLayout = () => (
  <>
    <Navbar />
    <main><Outlet /></main>
    <Chatbot />
  </>
);

// "/" sends people to the right home page for their role.
function HomeRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <Spinner fullPage />;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === "admin" ? "/admin" : "/dashboard"} replace />;
}

export default function App() {
  return (
    <ChatProvider>
      <Toaster position="top-right" toastOptions={{ duration: 3500 }} />
      <Routes>
        <Route path="/" element={<HomeRedirect />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Any logged-in user */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/tasks/new" element={<CreateTask />} />
            <Route path="/tasks/:id" element={<TaskDetails />} />
            <Route path="/tasks/:id/edit" element={<EditTask />} />
            <Route path="/profile" element={<Profile />} />
          </Route>
        </Route>

        {/* Regular users */}
        <Route element={<ProtectedRoute roles={["user"]} />}>
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<UserDashboard />} />
          </Route>
        </Route>

        {/* Admins only */}
        <Route element={<ProtectedRoute roles={["admin"]} />}>
          <Route element={<AppLayout />}>
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/admin/users" element={<UserManagement />} />
            <Route path="/admin/users/:id/tasks" element={<AdminUserTasks />} />
          </Route>
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
    </ChatProvider>
  );
}
