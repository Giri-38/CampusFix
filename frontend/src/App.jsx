import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Navbar from "./components/Navbar.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import StudentDashboard from "./pages/StudentDashboard.jsx";
import NewComplaint from "./pages/NewComplaint.jsx";
import ComplaintDetail from "./pages/ComplaintDetail.jsx";
import AdminDashboard from "./pages/AdminDashboard.jsx";

function Home() {
  const { user, loading } = useAuth();
  if (loading) return <p className="muted">Loading…</p>;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === "warden" ? "/admin" : "/dashboard"} replace />;
}

export default function App() {
  return (
    <>
      <Navbar />
      <main className="container">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute roles={["student"]}>
                <StudentDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/complaints/new"
            element={
              <ProtectedRoute roles={["student"]}>
                <NewComplaint />
              </ProtectedRoute>
            }
          />
          <Route
            path="/complaints/:id"
            element={
              <ProtectedRoute>
                <ComplaintDetail />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute roles={["warden"]}>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="*"
            element={
              <section className="card narrow">
                <h1>404</h1>
                <p>Page not found.</p>
              </section>
            }
          />
        </Routes>
      </main>
      <footer className="foot">CampusFix · hostel maintenance tracker</footer>
    </>
  );
}
