import { useEffect, useState } from "react";
import { GroupState, fetchGroupState } from "../api/client";
import { Fields } from "../components/Fields";

export function RiskPage() {
  const [state, setState] = useState<GroupState | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetchGroupState("A")
      .then(setState)
      .catch((err: unknown) => {
        setStatus(err instanceof Error ? err.message : "state unavailable");
      });
  }, []);

  const risk = state?.risk;
  return (
    <section>
      <h1>Risk & halts</h1>
      <Fields
        rows={[
          ["Halt", state?.halt_level || "none"],
          ["Kill", state?.kill_state || "none"],
          ["Halt command", risk?.halt_command || "none"],
          ["Partial halt", risk?.partial_halt ? "yes" : "no"],
          ["Trading revoked", risk?.trading_revoked ? "yes" : "no"],
          ["Exposure", risk?.exposure ?? "unknown"],
          ["Margin", risk?.margin ?? "unknown"],
          ["Distance to limits", risk?.distance_to_limits ?? "unknown"],
        ]}
      />
      {status ? <p role="status">{status}</p> : null}
    </section>
  );
}
