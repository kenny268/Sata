import { useEffect, useState } from "react";
import { fetchScoped } from "../api/client";
import { Fields } from "../components/Fields";

type CaseRow = { reimbursement_id?: string; status?: string; amount?: string };

export function TreasuryPage() {
  const [floor, setFloor] = useState("unknown");
  const [owed, setOwed] = useState("unknown");
  const [cases, setCases] = useState<CaseRow[]>([]);
  const [withdrawals, setWithdrawals] = useState<Array<string | { status?: string }>>([]);
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetchScoped<{
      cash_floor: string;
      reimbursement_owed: string;
      cases: CaseRow[];
      withdrawals: Array<string | { status?: string }>;
    }>("/treasury")
      .then((body) => {
        setFloor(body.cash_floor);
        setOwed(body.reimbursement_owed);
        setCases(body.cases);
        setWithdrawals(body.withdrawals);
      })
      .catch((err: unknown) => {
        setStatus(err instanceof Error ? err.message : "treasury unavailable");
      });
  }, []);

  return (
    <section>
      <h1>Treasury</h1>
      <Fields
        rows={[
          ["Cash floor", floor],
          ["Reimbursement owed", owed],
        ]}
      />
      <h2>Cases</h2>
      {cases.length === 0 ? <p>No reimbursement case</p> : null}
      <ul>
        {cases.map((item) => (
          <li key={item.reimbursement_id ?? item.amount}>
            {item.reimbursement_id} {item.status} {item.amount}
          </li>
        ))}
      </ul>
      <h2>Withdrawals</h2>
      {withdrawals.length === 0 ? <p>No withdrawal request</p> : null}
      <ul>
        {withdrawals.map((item, index) => (
          <li key={index}>{typeof item === "string" ? item : item.status ?? "withdrawal"}</li>
        ))}
      </ul>
      {status ? <p role="status">{status}</p> : null}
    </section>
  );
}
