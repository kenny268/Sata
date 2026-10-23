import { useEffect, useState } from "react";
import { fetchScoped } from "../api/client";

export function EligibilityPage() {
  const [reasons, setReasons] = useState<string[]>([]);
  const [gate, setGate] = useState(false);
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetchScoped<{ reason_codes: string[]; final_live_gate: boolean }>("/eligibility")
      .then((body) => {
        setReasons(body.reason_codes);
        setGate(body.final_live_gate);
      })
      .catch((err: unknown) => {
        setStatus(err instanceof Error ? err.message : "eligibility unavailable");
      });
  }, []);

  return (
    <section>
      <h1>Eligibility</h1>
      <p>Final LIVE gate {gate ? "open" : "closed"}</p>
      <ul>
        {reasons.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
      {status ? <p role="status">{status}</p> : null}
    </section>
  );
}
