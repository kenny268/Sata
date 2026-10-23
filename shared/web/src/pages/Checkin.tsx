import { FormEvent, useState } from "react";
import { postControl } from "../api/client";

export function CheckinPage() {
  const [passkey, setPasskey] = useState("");
  const [days, setDays] = useState("7");
  const [status, setStatus] = useState("");

  async function run(path: string, body: Record<string, unknown>) {
    try {
      const result = await postControl(path, body);
      setStatus(JSON.stringify(result));
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "check-in failed");
    }
  }

  function onCheckin(event: FormEvent) {
    event.preventDefault();
    void run("/checkin", { channel: "web_passkey", passkey_assertion: passkey });
  }

  return (
    <section>
      <h1>Check-in & away</h1>
      <form onSubmit={onCheckin}>
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
          Away days
          <input name="days" value={days} onChange={(event) => setDays(event.target.value)} />
        </label>
        <button type="submit">Check in</button>
        <button
          type="button"
          onClick={() => {
            void run("/checkin/away", {
              channel: "web_passkey",
              passkey_assertion: passkey,
              days: Number(days),
            });
          }}
        >
          Set away
        </button>
      </form>
      {status ? <p role="status">{status}</p> : null}
    </section>
  );
}
