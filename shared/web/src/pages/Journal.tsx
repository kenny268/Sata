import { useEffect, useState } from "react";
import { fetchScoped } from "../api/client";

type Entry = { seq: number; event_type: string; occurred_at: string; why: string };

export function JournalPage() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetchScoped<{ entries: Entry[]; why_from_log_only: boolean }>("/journal")
      .then((body) => setEntries(body.entries))
      .catch((err: unknown) => {
        setStatus(err instanceof Error ? err.message : "journal unavailable");
      });
  }, []);

  return (
    <section>
      <h1>Journal & Why</h1>
      <p>Why text comes from the fact log.</p>
      {entries.length === 0 ? <p>No journal entry</p> : null}
      <ul>
        {entries.map((entry) => (
          <li key={entry.seq}>
            {entry.event_type} {entry.occurred_at}: {entry.why}
          </li>
        ))}
      </ul>
      {status ? <p role="status">{status}</p> : null}
    </section>
  );
}
