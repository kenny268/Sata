import { useEffect, useState } from "react";
import { REPORTING_LABEL, fetchCombinedReporting } from "../api/client";

export function ReportingPage() {
  const [aEquity, setAEquity] = useState("unknown");
  const [bEquity, setBEquity] = useState("unknown");
  const [display, setDisplay] = useState("unknown");
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetchCombinedReporting()
      .then((report) => {
        setAEquity(report.a_equity);
        setBEquity(report.b_equity);
        setDisplay(report.combined_equity_display);
        setStatus(report.label);
      })
      .catch((err: unknown) => {
        setStatus(err instanceof Error ? err.message : "reporting failed");
      });
  }, []);

  return (
    <section className="reporting-only">
      <h1>Combined reporting</h1>
      <p>{REPORTING_LABEL}</p>
      <p>Group A equity {aEquity}</p>
      <p>Group B equity {bEquity}</p>
      <p>Combined display {display}</p>
      {status ? <p role="status">{status}</p> : null}
    </section>
  );
}
