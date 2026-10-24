import { REPORTING_LABEL } from "../api/client";

export function ReportingPage() {
  return (
    <section className="reporting-only">
      <h1>Combined reporting</h1>
      <p>{REPORTING_LABEL}</p>
    </section>
  );
}
