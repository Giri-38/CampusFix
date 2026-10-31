import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { PriorityPill, StatusPill } from "../components/Pill.jsx";
import { PRIORITY_COLORS, STATUS_COLORS, formatDate, toChartData } from "../utils.js";

const orDash = (v) => (v === null || v === undefined ? "-" : v);

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [meta, setMeta] = useState({ categories: [], statuses: [] });
  const [rows, setRows] = useState(null);
  const [filters, setFilters] = useState({ q: "", status: "", category: "" });
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.get("/stats"), api.get("/meta")])
      .then(([s, m]) => {
        setStats(s);
        setMeta(m);
      })
      .catch((e) => setError(e.message));
  }, []);

  // Re-query the list whenever a filter changes (search is debounced).
  useEffect(() => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => v && params.set(k, v));
    const timer = setTimeout(() => {
      api
        .get(`/complaints?${params}`)
        .then((d) => setRows(d.complaints))
        .catch((e) => setError(e.message));
    }, 250);
    return () => clearTimeout(timer);
  }, [filters]);

  if (error) return <div className="flash error">{error}</div>;
  if (!stats) return <p className="muted">Loading…</p>;

  const set = (key) => (e) => setFilters({ ...filters, [key]: e.target.value });

  return (
    <>
      <h1>Warden dashboard</h1>

      <div className="tiles">
        <div className="tile">
          <div className="num">{stats.total}</div>
          <div className="lbl">Total complaints</div>
        </div>
        <div className="tile">
          <div className="num">{stats.by_status.Open}</div>
          <div className="lbl">Open</div>
        </div>
        <div className="tile">
          <div className="num">{stats.resolution_rate}%</div>
          <div className="lbl">Resolution rate</div>
        </div>
        <div className="tile">
          <div className="num">{orDash(stats.avg_resolution_hours)}</div>
          <div className="lbl">Avg hours to resolve</div>
        </div>
        <div className="tile">
          <div className="num">{orDash(stats.avg_rating)}</div>
          <div className="lbl">Avg rating (of 5)</div>
        </div>
      </div>

      <div className="charts">
        <section className="card">
          <h2>By status</h2>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={toChartData(stats.by_status)} dataKey="value" nameKey="name" innerRadius={50} outerRadius={85} paddingAngle={2}>
                {toChartData(stats.by_status).map((d) => (
                  <Cell key={d.name} fill={STATUS_COLORS[d.name]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </section>

        <section className="card">
          <h2>By category</h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={toChartData(stats.by_category)}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" name="Complaints" fill="#3e63dd" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </section>

        <section className="card">
          <h2>Unresolved by priority</h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={toChartData(stats.open_by_priority)}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" name="Unresolved" radius={[4, 4, 0, 0]}>
                {toChartData(stats.open_by_priority).map((d) => (
                  <Cell key={d.name} fill={PRIORITY_COLORS[d.name]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </section>
      </div>

      <section className="card">
        <h2>All complaints</h2>
        <div className="row filters">
          <input placeholder="Search title, room or student" value={filters.q} onChange={set("q")} />
          <select value={filters.status} onChange={set("status")}>
            <option value="">All statuses</option>
            {meta.statuses.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
          <select value={filters.category} onChange={set("category")}>
            <option value="">All categories</option>
            {meta.categories.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
          <button className="link" onClick={() => setFilters({ q: "", status: "", category: "" })}>
            Clear
          </button>
        </div>

        {rows === null ? (
          <p className="muted">Loading…</p>
        ) : rows.length === 0 ? (
          <p className="muted">No complaints match these filters.</p>
        ) : (
          <div className="scroll">
            <table className="grid">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Title</th>
                  <th>Student</th>
                  <th>Room</th>
                  <th>Category</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((c) => (
                  <tr key={c.id}>
                    <td>{c.id}</td>
                    <td>
                      <Link to={`/complaints/${c.id}`}>{c.title}</Link>
                    </td>
                    <td>{c.student_name}</td>
                    <td>{c.room}</td>
                    <td>{c.category}</td>
                    <td>
                      <PriorityPill priority={c.priority} />
                    </td>
                    <td>
                      <StatusPill status={c.status} />
                    </td>
                    <td>{formatDate(c.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
