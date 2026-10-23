import { useEffect, useState } from "react";
import { ConstitutionView, fetchConstitution } from "../api/client";

export function ConstitutionPage() {
  const [view, setView] = useState<ConstitutionView | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetchConstitution()
      .then(setView)
      .catch((err: unknown) => {
        setStatus(err instanceof Error ? err.message : "constitution unavailable");
      });
  }, []);

  return (
    <section>
      <h1>Constitution</h1>
      <p>Read only</p>
      <p>Active version {view?.active_version ?? "none"}</p>
      <p>Time lock {view?.time_lock ?? "unset"}</p>
      <h2>Pending</h2>
      <ul>
        {(view?.pending ?? []).map((item) => (
          <li key={String(item.version)}>
            version {item.version ?? "none"}, {item.lock_state ?? "unset"}
            {item.eligible_at ? `, eligible ${item.eligible_at}` : ""}
          </li>
        ))}
      </ul>
      {(view?.pending ?? []).length === 0 ? <p>No pending change</p> : null}
      {status ? <p role="status">{status}</p> : null}
    </section>
  );
}
