export const STATUS_COLORS = { Open: "#e5484d", "In Progress": "#f5a524", Resolved: "#30a46c" };
export const PRIORITY_COLORS = { Low: "#8b8d98", Medium: "#f5a524", High: "#e5484d" };

/** "In Progress" -> "s-in-progress" (CSS class for a status pill). */
export const statusClass = (s) => "s-" + String(s).toLowerCase().replace(/\s+/g, "-");

/** "High" -> "p-high" (CSS class for a priority pill). */
export const priorityClass = (p) => "p-" + String(p).toLowerCase();

/** ISO timestamp -> "31 Oct 2026, 11:10 am"; "-" when empty; input echoed when unparseable. */
export function formatDate(iso) {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Count complaints per status, always including every status key. */
export function countByStatus(complaints, statuses) {
  const counts = Object.fromEntries(statuses.map((s) => [s, 0]));
  for (const c of complaints) if (c.status in counts) counts[c.status] += 1;
  return counts;
}

/** {Open: 3} -> [{name: "Open", value: 3}] for Recharts. */
export const toChartData = (obj) =>
  Object.entries(obj || {}).map(([name, value]) => ({ name, value }));
