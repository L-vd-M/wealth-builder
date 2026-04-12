const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function authHeaders(token?: string): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function fetchJson<T>(path: string, fallback: T, token?: string): Promise<T> {
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      cache: "no-store",
      headers: authHeaders(token),
    });
    if (!response.ok) {
      return fallback;
    }
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

export async function postJson<T, P>(path: string, payload: P, fallback: T, token?: string): Promise<T> {
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders(token) },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      return fallback;
    }
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}
