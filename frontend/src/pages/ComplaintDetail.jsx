import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { PriorityPill, StatusPill } from "../components/Pill.jsx";
import { formatDate, statusClass } from "../utils.js";

const STATUSES = ["Open", "In Progress", "Resolved"];

export default function ComplaintDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [comment, setComment] = useState("");
  const [status, setStatus] = useState("Open");
  const [note, setNote] = useState("");
  const [rating, setRating] = useState(5);

  const load = useCallback(() => {
    return api
      .get(`/complaints/${id}`)
      .then((d) => {
        setData(d);
        setStatus(d.complaint.status);
        setError("");
      })
      .catch((e) => setError(e.message));
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  // Runs an API action, then refreshes the page data and shows feedback.
  const act = async (fn, okMessage) => {
    setNotice("");
    try {
      await fn();
      await load();
      setNotice(okMessage);
    } catch (e) {
      setError(e.message);
    }
  };

  if (error && !data) {
    return (
      <>
        <div className="flash error">{error}</div>
        <Link to="/">← Back</Link>
      </>
    );
  }
  if (!data) return <p className="muted">Loading…</p>;

  const { complaint: c, timeline } = data;
  const isWarden = user.role === "warden";

  return (
    <>
      <div className="row between">
        <h1>
          #{c.id} · {c.title}
        </h1>
        <StatusPill status={c.status} big />
      </div>
      {notice && <div className="flash ok">{notice}</div>}
      {error && <div className="flash error">{error}</div>}

      <section className="card">
        <p className="pre">{c.description}</p>
        <dl className="meta">
          <div>
            <dt>Raised by</dt>
            <dd>{c.student_name}</dd>
          </div>
          <div>
            <dt>Room</dt>
            <dd>{c.room}</dd>
          </div>
          <div>
            <dt>Category</dt>
            <dd>{c.category}</dd>
          </div>
          <div>
            <dt>Priority</dt>
            <dd>
              <PriorityPill priority={c.priority} />
            </dd>
          </div>
          <div>
            <dt>Created</dt>
            <dd>{formatDate(c.created_at)}</dd>
          </div>
          <div>
            <dt>Resolved</dt>
            <dd>{formatDate(c.resolved_at)}</dd>
          </div>
        </dl>
      </section>

      {isWarden && (
        <section className="card">
          <h2>Update status</h2>
          <form
            className="row"
            onSubmit={(e) => {
              e.preventDefault();
              act(async () => {
                await api.post(`/complaints/${id}/status`, { status, note });
                setNote("");
              }, `Status set to ${status}.`);
            }}
          >
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              {STATUSES.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
            <input
              placeholder="Optional note for the student"
              maxLength={500}
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
            <button className="btn" type="submit">
              Save
            </button>
          </form>
        </section>
      )}

      {!isWarden && c.status === "Resolved" && (
        <section className="card">
          <h2>How was the fix?</h2>
          {c.rating ? (
            <p>
              You rated this <strong>{c.rating} / 5</strong>. Thank you!
            </p>
          ) : (
            <form
              className="row"
              onSubmit={(e) => {
                e.preventDefault();
                act(() => api.post(`/complaints/${id}/rating`, { rating: Number(rating) }), "Thanks for your feedback!");
              }}
            >
              <select value={rating} onChange={(e) => setRating(e.target.value)}>
                {[5, 4, 3, 2, 1].map((n) => (
                  <option key={n} value={n}>
                    {n} / 5
                  </option>
                ))}
              </select>
              <button className="btn" type="submit">
                Submit rating
              </button>
            </form>
          )}
        </section>
      )}

      <section className="card">
        <h2>Timeline</h2>
        <ol className="timeline">
          {timeline.map((t) => (
            <li key={t.id}>
              <div className="who">
                {t.name}
                {t.role === "warden" && <span className="pill p-low">warden</span>}
                <span className="muted"> · {formatDate(t.created_at)} </span>
                {t.status_change && <span className={`pill ${statusClass(t.status_change)}`}>{t.status_change}</span>}
              </div>
              <div className="pre">{t.message}</div>
            </li>
          ))}
        </ol>
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault();
            act(async () => {
              await api.post(`/complaints/${id}/comments`, { message: comment });
              setComment("");
            }, "Comment added.");
          }}
        >
          <textarea
            rows={3}
            required
            maxLength={1000}
            placeholder="Add a comment..."
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
          <button className="btn" type="submit">
            Post comment
          </button>
        </form>
      </section>
    </>
  );
}
