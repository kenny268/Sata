import { useEffect, useState } from "react";
import { fetchScoped } from "../api/client";
import { Fields } from "../components/Fields";

export function HealthPage() {
  const [heartbeat, setHeartbeat] = useState("unknown");
  const [broker, setBroker] = useState("unknown");
  const [chain, setChain] = useState("unknown");
  const [replay, setReplay] = useState("0");
  const [notes, setNotes] = useState<string[]>([]);
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetchScoped<{
      process_heartbeat: boolean;
      broker: string;
      hash_chain: string;
      replay_events: number;
      notifications: string[];
    }>("/health")
      .then((body) => {
        setHeartbeat(body.process_heartbeat ? "ok" : "down");
        setBroker(body.broker);
        setChain(body.hash_chain);
        setReplay(String(body.replay_events));
        setNotes(body.notifications);
      })
      .catch((err: unknown) => {
        setStatus(err instanceof Error ? err.message : "health unavailable");
      });
  }, []);

  return (
    <section>
      <h1>System health</h1>
      <Fields
        rows={[
          ["Process heartbeat", heartbeat],
          ["Broker", broker],
          ["Hash chain", chain],
          ["Replay events", replay],
        ]}
      />
      <h2>Notifications</h2>
      {notes.length === 0 ? <p>No notification</p> : null}
      <ul>
        {notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>
      {status ? <p role="status">{status}</p> : null}
    </section>
  );
}
