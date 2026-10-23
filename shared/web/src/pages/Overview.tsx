import { useEffect, useState } from "react";
import { GroupState, fetchGroupState } from "../api/client";
import { Fields } from "../components/Fields";
import { ModeBadge } from "../components/ModeBadge";

const empty = "unknown";

export function OverviewPage() {
  const [state, setState] = useState<GroupState | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetchGroupState("A")
      .then(setState)
      .catch((err: unknown) => {
        setStatus(err instanceof Error ? err.message : "state unavailable");
      });
  }, []);

  const capital = state?.capital;
  return (
    <section>
      <h1>Overview</h1>
      <p>
        Mode{" "}
        <ModeBadge
          mode={state?.mode ?? "SIM"}
          color={state?.mode_badge.color ?? "blue"}
          tag={state?.mode_badge.tag ?? "A-SIM"}
        />
      </p>
      <h2>Capital hierarchy</h2>
      <Fields
        rows={[
          ["Equity", capital?.equity ?? empty],
          ["Reserved", capital?.reserved ?? empty],
          ["Withdrawable", capital?.withdrawable ?? empty],
          ["RCB", capital?.ratified_base ?? empty],
        ]}
      />
      <h2>Activity</h2>
      <Fields
        rows={[
          ["Arming", state?.arming.phase ?? "idle"],
          ["Halt command", state?.risk.halt_command || "none"],
        ]}
      />
      <h2>Attention</h2>
      <ul>
        {(state?.attention ?? []).map((flag) => (
          <li key={flag}>{flag}</li>
        ))}
      </ul>
      {status ? <p role="status">{status}</p> : null}
    </section>
  );
}
