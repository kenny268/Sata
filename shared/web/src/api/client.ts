/** Typed facade over control-api routes (private network). */

export type ModeBadge = { color: string; tag: string };

export type CapitalBook = {
  equity: string;
  realised_pnl: string;
  settled: string;
  reserved: string;
  withdrawable: string;
  ratified_base: string;
  pending_obligations: string;
};

export type GroupState = {
  mode: string;
  halt_level: string;
  kill_state: string;
  mode_badge: ModeBadge;
  capital: CapitalBook;
  attention: string[];
  risk: {
    exposure: string;
    margin: string;
    distance_to_limits: string;
    partial_halt: boolean;
    trading_revoked: boolean;
    halt_command: string;
  };
  arming: { phase: string; reasons: string[] };
  constitution: {
    loaded: boolean;
    active_version: number | null;
    pending_count: number;
    time_lock: string;
  };
};

export type ConstitutionView = {
  read_only: boolean;
  active_version: number | null;
  time_lock: string;
  pending: Array<{
    version?: number;
    reason?: string;
    lock_state?: string;
    eligible_at?: string | null;
  }>;
  live_blockers?: string[];
};

export type CombinedReport = {
  a_equity: string;
  b_equity: string;
  combined_equity_display: string;
  reporting_only: boolean;
  label: string;
};

let csrfToken: string | null = null;

async function ensureCsrf(): Promise<string> {
  if (csrfToken) {
    return csrfToken;
  }
  const response = await fetch("/api/csrf");
  if (!response.ok) {
    throw new Error("csrf fetch failed");
  }
  const body = (await response.json()) as { csrf_token: string };
  csrfToken = body.csrf_token;
  return csrfToken;
}

export async function fetchGroupState(scope: "A" | "B"): Promise<GroupState> {
  const response = await fetch(`/api/state?scope=${scope}`);
  if (!response.ok) {
    throw new Error("state fetch failed");
  }
  return response.json();
}

export async function fetchConstitution(): Promise<ConstitutionView> {
  const response = await fetch("/api/constitution?scope=A");
  if (!response.ok) {
    throw new Error("constitution fetch failed");
  }
  return response.json();
}

export async function fetchScoped<T>(path: string, scope: "A" | "B" = "A"): Promise<T> {
  const response = await fetch(`/api${path}?scope=${scope}`);
  if (!response.ok) {
    throw new Error(`${path} fetch failed`);
  }
  return response.json() as Promise<T>;
}

export async function fetchCombinedReporting(): Promise<CombinedReport> {
  const response = await fetch("/api/reporting/combined");
  if (!response.ok) {
    throw new Error("reporting fetch failed");
  }
  return response.json();
}

export async function postControl(path: string, body: Record<string, unknown>): Promise<unknown> {
  const token = await ensureCsrf();
  const response = await fetch(`/api${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": token,
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    let detail = String(response.status);
    try {
      const payload = (await response.json()) as { error?: string };
      if (payload.error) {
        detail = payload.error;
      }
    } catch {
      detail = String(response.status);
    }
    throw new Error(detail);
  }
  return response.json();
}

export const REPORTING_LABEL =
  "Combined reporting — not transferable and not used for sizing or eligibility";
