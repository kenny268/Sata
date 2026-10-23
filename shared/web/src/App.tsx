import { useEffect, useState } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { CapitalPage } from "./pages/Capital";
import { CheckinPage } from "./pages/Checkin";
import { ConstitutionPage } from "./pages/Constitution";
import { ControlsPage } from "./pages/Controls";
import { EligibilityPage } from "./pages/Eligibility";
import { HealthPage } from "./pages/Health";
import { JournalPage } from "./pages/Journal";
import { OverviewPage } from "./pages/Overview";
import { PerformancePage } from "./pages/Performance";
import { PositionsPage } from "./pages/Positions";
import { ReportingPage } from "./pages/Reporting";
import { RiskPage } from "./pages/Risk";
import { TreasuryPage } from "./pages/Treasury";

const groups = [
  {
    label: "Book",
    links: [
      ["/", "Overview"],
      ["/capital", "Capital"],
      ["/positions", "Positions"],
      ["/performance", "Performance"],
    ],
  },
  {
    label: "Risk",
    links: [
      ["/eligibility", "Eligibility"],
      ["/risk", "Risk"],
      ["/journal", "Journal"],
    ],
  },
  {
    label: "Desk",
    links: [
      ["/treasury", "Treasury"],
      ["/controls", "Controls"],
      ["/checkin", "Check-in"],
      ["/constitution", "Constitution"],
      ["/health", "Health"],
      ["/reporting", "Reporting"],
    ],
  },
] as const;

function navClass(isActive: boolean) {
  return [
    "block rounded-lg px-3 py-2 text-sm transition-colors duration-200",
    isActive ? "bg-ink text-white" : "text-mute hover:bg-paper hover:text-ink",
  ].join(" ");
}

export default function App() {
  const [open, setOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="min-h-screen bg-paper text-ink">
      <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-line bg-white px-4 py-3 lg:hidden">
        <button
          type="button"
          className="menu-button"
          aria-expanded={open}
          aria-controls="desk-nav"
          onClick={() => setOpen((value) => !value)}
        >
          <span className="sr-only">{open ? "Close menu" : "Open menu"}</span>
          <span className={`menu-bar ${open ? "translate-y-[5px] rotate-45" : ""}`} />
          <span className={`menu-bar ${open ? "opacity-0" : ""}`} />
          <span className={`menu-bar ${open ? "-translate-y-[5px] -rotate-45" : ""}`} />
        </button>
        <p className="text-sm font-semibold sm:text-base">Group A</p>
      </header>

      {open ? (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-ink/40 lg:hidden"
          aria-label="Close menu"
          onClick={() => setOpen(false)}
        />
      ) : null}

      <aside
        id="desk-nav"
        className={[
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-line bg-white px-4 py-6 transition-transform duration-200 lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        ].join(" ")}
      >
        <p className="px-3 text-xs font-semibold uppercase tracking-[0.16em] text-mute">SATE</p>
        <p className="mb-6 px-3 text-lg font-semibold text-ink">Group A</p>
        <nav className="flex flex-1 flex-col gap-6 overflow-y-auto">
          {groups.map((group) => (
            <div key={group.label}>
              <p className="mb-1 px-3 text-xs font-medium text-mute">{group.label}</p>
              {group.links.map(([path, label]) => (
                <NavLink key={path} to={path} end={path === "/"} className={({ isActive }) => navClass(isActive)}>
                  {label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </aside>

      <div className="lg:pl-64">
        <header className="hidden items-center justify-between border-b border-line bg-white px-8 py-4 lg:flex">
          <p className="text-base font-medium text-ink">Group A book</p>
          <p className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-800">Desk open</p>
        </header>
        <main className="px-4 py-5 sm:px-6 sm:py-6 lg:px-8 lg:py-8">
          <Routes>
            <Route path="/" element={<OverviewPage />} />
            <Route path="/capital" element={<CapitalPage />} />
            <Route path="/positions" element={<PositionsPage />} />
            <Route path="/performance" element={<PerformancePage />} />
            <Route path="/eligibility" element={<EligibilityPage />} />
            <Route path="/risk" element={<RiskPage />} />
            <Route path="/journal" element={<JournalPage />} />
            <Route path="/treasury" element={<TreasuryPage />} />
            <Route path="/controls" element={<ControlsPage />} />
            <Route path="/checkin" element={<CheckinPage />} />
            <Route path="/constitution" element={<ConstitutionPage />} />
            <Route path="/health" element={<HealthPage />} />
            <Route path="/reporting" element={<ReportingPage />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
