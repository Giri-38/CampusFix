import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", room: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api.post("/auth/register", form);
      navigate("/login", { state: { registered: true } });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card narrow">
      <h1>Create a student account</h1>
      {error && <div className="flash error">{error}</div>}
      <form onSubmit={onSubmit}>
        <label>
          Full name
          <input required maxLength={80} value={form.name} onChange={set("name")} />
        </label>
        <label>
          Email
          <input type="email" required value={form.email} onChange={set("email")} />
        </label>
        <label>
          Room number
          <input required maxLength={20} placeholder="e.g. B-204" value={form.room} onChange={set("room")} />
        </label>
        <label>
          Password
          <input type="password" required minLength={8} value={form.password} onChange={set("password")} />
        </label>
        <button className="btn" type="submit" disabled={busy}>
          {busy ? "Creating…" : "Register"}
        </button>
      </form>
      <p className="muted">
        Already registered? <Link to="/login">Log in</Link>.
      </p>
    </section>
  );
}
