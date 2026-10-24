import { postControl } from "../api/client";

export function ControlsPage() {
  return (
    <section>
      <h1>Controls</h1>
      <p>SIM/LIVE arming wizard, preflight reason codes, resume, kill — passkey on risk-increasing steps.</p>
      <button
        type="button"
        onClick={() => {
          void postControl("/mode/A/cancel", {}).catch(() => undefined);
        }}
      >
        Cancel arming (AM-02)
      </button>
      <ol>
        <li>POST /mode/A/arm — preflight + 24h delay</li>
        <li>POST /mode/A/confirm — OTP from Telegram, entered in web only</li>
        <li>POST /mode/A/sim — LIVE → SIM (passkey)</li>
      </ol>
    </section>
  );
}
