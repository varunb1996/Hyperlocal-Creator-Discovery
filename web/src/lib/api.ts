// Server-side FastAPI client. Imported only by server components and server actions:
// the browser never calls the API (or Supabase) directly.
import type { ShortlistResponse, Vocab } from "./types";

const API_URL = process.env.API_URL;

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  if (!API_URL) throw new ApiError("API_URL is not set (see web/.env.example).", 500);
  let res: Response;
  try {
    res = await fetch(`${API_URL.replace(/\/$/, "")}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
      cache: "no-store",
    });
  } catch {
    throw new ApiError("Can't reach the ranking service. Check that the backend is running.", 503);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : `Request failed (${res.status}).`;
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

export const getVocab = () => call<Vocab>("/vocab");

export const getShortlist = (id: string) => call<ShortlistResponse>(`/shortlist/${encodeURIComponent(id)}`);

export const postShortlist = (brief: Record<string, unknown>) =>
  call<ShortlistResponse>("/shortlist", { method: "POST", body: JSON.stringify(brief) });
