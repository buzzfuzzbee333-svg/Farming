const BASE = process.env.EXPO_PUBLIC_BACKEND_URL;

if (!BASE) {
  console.warn("EXPO_PUBLIC_BACKEND_URL is not set");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE}/api${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

export type TapPoint = { x: number; y: number };
export type GameConfig = {
  name: string;
  package_name: string;
  tap_regions: Record<string, TapPoint>;
  loop: Record<string, number>;
  safety: Record<string, number>;
};

export type IdleGame = {
  id: string;
  name: string;
  package_name: string;
  platform: string;
  base_payout_cents: number;
  est_minutes: number;
  config_json: GameConfig;
  automate_flow_json?: Record<string, any> | null;
  is_active: boolean;
  created_at: string;
};

export type IdleSession = {
  id: string;
  game_id: string;
  game_name?: string;
  session_minutes: number;
  started_at: string;
  ended_at?: string | null;
  status: "running" | "completed" | "failed" | "aborted";
  notes?: string | null;
  earned_cents: number;
};

export type IdleMilestone = {
  id: string;
  game_id: string;
  label: string;
  target_desc: string;
  est_minutes: number;
  payout_cents: number;
  order_index: number;
  completed: boolean;
};

export type DashboardStats = {
  total_earnings_cents: number;
  active_sessions: number;
  completed_sessions: number;
  failed_sessions: number;
  total_runtime_minutes: number;
  total_games: number;
  recent_sessions: IdleSession[];
};

export const api = {
  dashboard: () => request<DashboardStats>("/dashboard"),

  listGames: () => request<IdleGame[]>("/games"),
  getGame: (id: string) => request<IdleGame>(`/games/${id}`),
  createGame: (body: Partial<IdleGame>) =>
    request<IdleGame>("/games", { method: "POST", body: JSON.stringify(body) }),
  updateGame: (id: string, body: Partial<IdleGame>) =>
    request<IdleGame>(`/games/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteGame: (id: string) =>
    request<{ deleted: boolean }>(`/games/${id}`, { method: "DELETE" }),

  listSessions: (params: { game_id?: string; status?: string } = {}) => {
    const qs = new URLSearchParams();
    if (params.game_id) qs.append("game_id", params.game_id);
    if (params.status) qs.append("status", params.status);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<IdleSession[]>(`/sessions${suffix}`);
  },
  createSession: (body: { game_id: string; session_minutes: number; notes?: string }) =>
    request<IdleSession>("/sessions", { method: "POST", body: JSON.stringify(body) }),
  updateSession: (id: string, body: Partial<IdleSession>) =>
    request<IdleSession>(`/sessions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  stopSession: (id: string) =>
    request<IdleSession>(`/sessions/${id}/stop`, { method: "POST" }),
  deleteSession: (id: string) =>
    request<{ deleted: boolean }>(`/sessions/${id}`, { method: "DELETE" }),

  listMilestones: (game_id?: string) =>
    request<IdleMilestone[]>(
      `/milestones${game_id ? `?game_id=${game_id}` : ""}`
    ),
  createMilestone: (body: Partial<IdleMilestone>) =>
    request<IdleMilestone>("/milestones", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateMilestone: (id: string, body: Partial<IdleMilestone>) =>
    request<IdleMilestone>(`/milestones/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteMilestone: (id: string) =>
    request<{ deleted: boolean }>(`/milestones/${id}`, { method: "DELETE" }),
};
