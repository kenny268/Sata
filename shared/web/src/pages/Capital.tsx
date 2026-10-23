import { FormEvent, useEffect, useState } from "react";
import { CapitalBook, fetchGroupState, postControl } from "../api/client";
import { Fields } from "../components/Fields";

export function CapitalPage() {
  const [book, setBook] = useState<CapitalBook | null>(null);
  const [passkey, setPasskey] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetchGroupState("A")
      .then((state) => setBook(state.capital))
      .catch((err: unknown) => {
        setStatus(err instanceof Error ? err.message : "capital unavailable");
      });
  }, []);

  function onRatify(event: FormEvent) {
    event.preventDefault();
    void postControl("/capital/ratify", { passkey_assertion: passkey })
      .then((result) => setStatus(JSON.stringify(result)))
      .catch((err: unknown) => {
        setStatus(err instanceof Error ? err.message : "ratify failed");
      });
  }

  return (
    <section>
      <h1>Capital</h1>
      <Fields
        rows={[
          ["Equity", book?.equity ?? "unknown"],
          ["Realised P&L", book?.realised_pnl ?? "unknown"],
          ["Settled", book?.settled ?? "unknown"],
          ["Reserved", book?.reserved ?? "unknown"],
          ["Withdrawable", book?.withdrawable ?? "unknown"],
          ["Pending obligations", book?.pending_obligations ?? "unknown"],
          ["RCB", book?.ratified_base ?? "unknown"],
        ]}
      />
      <form onSubmit={onRatify}>
        <label>
          Passkey assertion
          <input
            name="passkey"
            value={passkey}
            autoComplete="off"
            onChange={(event) => setPasskey(event.target.value)}
          />
        </label>
        <button type="submit">Ratify RCB</button>
      </form>
      {status ? <p role="status">{status}</p> : null}
    </section>
  );
}
