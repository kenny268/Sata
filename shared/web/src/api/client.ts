/** Typed facade over control-api routes (private network). */

export type ModeBadge = { color: string; tag: string };

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

export async function fetchGroupState(scope: "A" | "B"): Promise<{
  mode: string;
  mode_badge: ModeBadge;
}> {
  const response = await fetch(`/api/state?scope=${scope}&mode=SIM`);
  if (!response.ok) {
    throw new Error("state fetch failed");
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
    throw new Error(`control post failed: ${response.status}`);
  }
  return response.json();
}

export const REPORTING_LABEL =
  "Combined reporting — not transferable and not used for sizing or eligibility";
