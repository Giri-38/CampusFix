import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";

export default function NewComplaint() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [meta, setMeta] = useState({ categories: [], priorities: [] });
  const [form, setForm] = useState({
    title: "",
    description: "",
    category: "Electrical",
    priority: "Medium",
    room: user?.room || "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get("/meta").then(setMeta).catch((e) => setError(e.message));
  }, []);

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const d = await api.post("/complaints", form);
      navigate(`/complaints/${d.complaint.id}`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <section className="card narrow">
      <h1>Raise a complaint</h1>
      {error && <div className="flash error">{error}</div>}
      <form onSubmit={onSubmit}>
        <label>
          Title
          <input required minLength={5} maxLength={120} value={form.title} onChange={set("title")} />
        </label>
        <label>
          Describe the problem
          <textarea
            rows={5}
            required
            minLength={10}
            maxLength={2000}
            value={form.description}
            onChange={set("description")}
          />
        </label>
        <div className="two">
          <label>
            Category
            <select value={form.category} onChange={set("category")}>
              {meta.categories.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </label>
          <label>
            Priority
            <select value={form.priority} onChange={set("priority")}>
              {meta.priorities.map((p) => (
                <option key={p}>{p}</option>
              ))}
            </select>
          </label>
        </div>
        <label>
          Room
          <input required maxLength={20} value={form.room} onChange={set("room")} />
        </label>
        <button className="btn" type="submit" disabled={busy}>
          {busy ? "Submitting…" : "Submit complaint"}
        </button>
      </form>
    </section>
  );
}
