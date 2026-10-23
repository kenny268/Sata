import { useEffect, useState } from "react";
import { fetchScoped } from "../api/client";
import { Fields } from "../components/Fields";

type Position = {
  instrument: string;
  quantity: string;
  stop: string;
  pending: string;
  fill_price: string;
  slippage: string;
};

export function PositionsPage() {
  const [rows, setRows] = useState<Position[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetchScoped<{ loaded: boolean; positions: Position[] }>("/positions")
      .then((body) => {
        setLoaded(body.loaded);
        setRows(body.positions);
      })
      .catch((err: unknown) => {
        setStatus(err instanceof Error ? err.message : "positions unavailable");
      });
  }, []);

  return (
    <section>
      <h1>Positions & orders</h1>
      {loaded ? null : <p>Book unloaded</p>}
      {rows.length === 0 ? <p>No open position</p> : null}
      {rows.map((row) => (
        <Fields
          key={row.instrument}
          rows={[
            ["Instrument", row.instrument || "unknown"],
            ["Quantity", row.quantity || "unknown"],
            ["Stop", row.stop || "unknown"],
            ["Pending", row.pending || "none"],
            ["Fill", row.fill_price || "none"],
            ["Slippage", row.slippage || "unknown"],
          ]}
        />
      ))}
      {status ? <p role="status">{status}</p> : null}
    </section>
  );
}
