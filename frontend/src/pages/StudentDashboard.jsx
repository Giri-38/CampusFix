import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { PriorityPill, StatusPill } from "../components/Pill.jsx";
import { countByStatus, formatDate } from "../utils.js";

const STATUSES = ["Open", "In Progress", "Resolved"];

export default function StudentDashboard() {
  const [complaints, setComplaints] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/complaints")
      .then((d) => setComplaints(d.complaints))
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="flash error">{error}</div>;
  if (!complaints) return <p className="muted">Loading…</p>;

  const counts = countByStatus(complaints, STATUSES);

  return (
    <>
      <div className="row between">
        <h1>My complaints</h1>
        <Link className="btn" to="/complaints/new">
          + New complaint
        </Link>
      </div>

      <div className="tiles">
        {STATUSES.map((s) => (
          <div className="tile" key={s}>
            <div className="num">{counts[s]}</div>
            <div className="lbl">{s}</div>
          </div>
        ))}
      </div>

      {complaints.length === 0 ? (
        <p className="muted">You have not raised any complaints yet.</p>
      ) : (
        <div className="scroll">
          <table className="grid">
            <thead>
              <tr>
                <th>#</th>
                <th>Title</th>
                <th>Category</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {complaints.map((c) => (
                <tr key={c.id}>
                  <td>{c.id}</td>
                  <td>
                    <Link to={`/complaints/${c.id}`}>{c.title}</Link>
                  </td>
                  <td>{c.category}</td>
                  <td>
                    <PriorityPill priority={c.priority} />
                  </td>
                  <td>
                    <StatusPill status={c.status} />
                  </td>
                  <td>{formatDate(c.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
