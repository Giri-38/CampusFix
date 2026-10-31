import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth.jsx";

/** Redirects anonymous visitors to /login and wrong-role users to their own home. */
export default function ProtectedRoute({ roles, children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <p className="muted">Loading…</p>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}
