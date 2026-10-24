import { NavLink, Route, Routes } from "react-router-dom";
import { CapitalPage } from "./pages/Capital";
import { CheckinPage } from "./pages/Checkin";
import { ConstitutionPage } from "./pages/Constitution";
import { ControlsPage } from "./pages/Controls";
import { OverviewPage } from "./pages/Overview";
import { ReportingPage } from "./pages/Reporting";
import { RiskPage } from "./pages/Risk";

const links = [
  ["/", "Overview"],
  ["/capital", "Capital"],
  ["/risk", "Risk & halts"],
  ["/controls", "Controls"],
  ["/checkin", "Check-in"],
  ["/constitution", "Constitution"],
  ["/reporting", "Combined reporting"],
] as const;

export default function App() {
  return (
    <div className="layout">
      <nav>
        <p style={{ padding: "1rem", fontWeight: 600 }}>Group A</p>
        {links.map(([path, label]) => (
          <NavLink key={path} to={path} end={path === "/"}>
            {label}
          </NavLink>
        ))}
      </nav>
      <main>
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/capital" element={<CapitalPage />} />
          <Route path="/risk" element={<RiskPage />} />
          <Route path="/controls" element={<ControlsPage />} />
          <Route path="/checkin" element={<CheckinPage />} />
          <Route path="/constitution" element={<ConstitutionPage />} />
          <Route path="/reporting" element={<ReportingPage />} />
        </Routes>
      </main>
    </div>
  );
}
