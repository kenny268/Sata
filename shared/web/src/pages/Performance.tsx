import { useEffect, useState } from "react";
import { fetchScoped } from "../api/client";
import { Fields } from "../components/Fields";

type Book = {
  net_of_cost: string;
  attribution: string;
  drawdown: string;
  benchmark: string;
};

export function PerformancePage() {
  const [sim, setSim] = useState<Book | null>(null);
  const [live, setLive] = useState<Book | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetchScoped<{ books: { SIM: Book; LIVE: Book } }>("/performance")
      .then((body) => {
        setSim(body.books.SIM);
        setLive(body.books.LIVE);
      })
      .catch((err: unknown) => {
        setStatus(err instanceof Error ? err.message : "performance unavailable");
      });
  }, []);

  return (
    <section>
      <h1>Performance</h1>
      <p>SIM and LIVE stay in separate books.</p>
      <h2>SIM</h2>
      <Fields
        rows={[
          ["Net of cost", sim?.net_of_cost ?? "unknown"],
          ["Attribution", sim?.attribution ?? "unknown"],
          ["Drawdown", sim?.drawdown ?? "unknown"],
          ["Benchmark", sim?.benchmark ?? "unknown"],
        ]}
      />
      <h2>LIVE</h2>
      <Fields
        rows={[
          ["Net of cost", live?.net_of_cost ?? "unknown"],
          ["Attribution", live?.attribution ?? "unknown"],
          ["Drawdown", live?.drawdown ?? "unknown"],
          ["Benchmark", live?.benchmark ?? "unknown"],
        ]}
      />
      {status ? <p role="status">{status}</p> : null}
    </section>
  );
}
