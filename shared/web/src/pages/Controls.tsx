import { FormEvent, useState } from "react";
import { postControl } from "../api/client";

type ArmResult = {
  status?: string;
  reasons?: string;
  halt_state?: string;
  steps?: string[];
};

export function ControlsPage() {
  const [passkey, setPasskey] = useState("");
  const [otp, setOtp] = useState("");
  const [cleanRecon, setCleanRecon] = useState(true);
  const [status, setStatus] = useState("");
  const [reasons, setReasons] = useState<string[]>([]);

  async function run(path: string, body: Record<string, unknown>) {
    try {
      const result = (await postControl(path, body)) as ArmResult;
      const steps = result.steps?.length ? result.steps.join(", ") : "";
      setStatus(steps ? `${result.status}: ${steps}` : result.status || result.halt_state || "accepted");
      setReasons(
        result.reasons
          ? result.reasons.split(",").map((item) => item.trim()).filter(Boolean)
          : [],
      );
    } catch (err) {
      setReasons([]);
      setStatus(err instanceof Error ? err.message : "control failed");
    }
  }

  function onSim(event: FormEvent) {
    event.preventDefault();
    void run("/mode/A/sim", { passkey_assertion: passkey });
  }

  return (
    <section>
      <h1>Controls</h1>
      <p>SIM operations from the web. A passkey assertion is required before a risk-increasing step.</p>
      <form onSubmit={onSim}>
        <label>
          Passkey assertion
          <input
            name="passkey"
            value={passkey}
            autoComplete="off"
            onChange={(event) => setPasskey(event.target.value)}
          />
        </label>
        <label>
          OTP
          <input name="otp" value={otp} autoComplete="off" onChange={(event) => setOtp(event.target.value)} />
        </label>
        <label>
          <input
            name="clean_recon"
            type="checkbox"
            checked={cleanRecon}
            onChange={(event) => setCleanRecon(event.target.checked)}
          />
          Clean reconciliation
        </label>
        <button type="submit">Switch to SIM</button>
        <button type="button" onClick={() => void run("/mode/A/cancel", {})}>
          Cancel arming
        </button>
        <button
          type="button"
          onClick={() =>
            void run("/mode/A/arm", {
              passkey_assertion: passkey,
              otp,
              scope: "A",
              clean_recon: cleanRecon,
            })
          }
        >
          Start arming
        </button>
        <button
          type="button"
          onClick={() => void run("/mode/A/confirm", { passkey_assertion: passkey, code: otp })}
        >
          Confirm OTP
        </button>
        <button type="button" onClick={() => void run("/resume/A", { passkey_assertion: passkey, channel: "web" })}>
          Resume
        </button>
        <button type="button" onClick={() => void run("/kill", { scope: "A", kill_level: "K1", channel: "web" })}>
          Kill K1
        </button>
      </form>
      {reasons.length > 0 ? (
        <div>
          <h2>Preflight</h2>
          <ul>
            {reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {status ? <p role="status">{status}</p> : null}
    </section>
  );
}
