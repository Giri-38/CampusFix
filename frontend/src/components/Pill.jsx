import { priorityClass, statusClass } from "../utils.js";

export const StatusPill = ({ status, big }) => (
  <span className={`pill ${statusClass(status)}${big ? " big" : ""}`}>{status}</span>
);

export const PriorityPill = ({ priority }) => (
  <span className={`pill ${priorityClass(priority)}`}>{priority}</span>
);
