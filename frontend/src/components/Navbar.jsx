import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const onLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header className="topbar">
      <Link className="brand" to="/">
        Campus<span>Fix</span>
      </Link>
      <nav>
        {user ? (
          <>
            {user.role === "warden" ? (
              <Link to="/admin">Dashboard</Link>
            ) : (
              <>
                <Link to="/dashboard">My complaints</Link>
                <Link to="/complaints/new">New complaint</Link>
              </>
            )}
            <span className="who">
              {user.name} · {user.role}
            </span>
            <button className="link" onClick={onLogout}>
              Log out
            </button>
          </>
        ) : (
          <>
            <Link to="/login">Log in</Link>
            <Link to="/register">Register</Link>
          </>
        )}
      </nav>
    </header>
  );
}
