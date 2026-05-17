import type { GraphData, DashboardData, DetailEntityV3, SearchResults, SummaryData, WorldViewData } from '../types/api';

const API_BASE = '/api';

export async function fetchGraph(): Promise<GraphData> {
  const res = await fetch(`${API_BASE}/graph`);
  if (!res.ok) throw new Error(`Graph API error: ${res.status}`);
  return res.json() as Promise<GraphData>;
}

export async function fetchDashboard(): Promise<DashboardData> {
  const res = await fetch(`${API_BASE}/dashboard`);
  if (!res.ok) throw new Error(`Dashboard API error: ${res.status}`);
  return res.json() as Promise<DashboardData>;
}

export async function fetchDetail(entityId: string): Promise<DetailEntityV3> {
  const res = await fetch(`${API_BASE}/detail/entity/${encodeURIComponent(entityId)}`);
  if (!res.ok) throw new Error(`Detail API error: ${res.status} for entity/${entityId}`);
  return res.json() as Promise<DetailEntityV3>;
}

export async function fetchSearch(q: string): Promise<SearchResults> {
  const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(q)}`);
  if (!res.ok) throw new Error(`Search API error: ${res.status}`);
  return res.json() as Promise<SearchResults>;
}

export async function fetchSummary(): Promise<SummaryData> {
  const res = await fetch(`${API_BASE}/summary`);
  if (!res.ok) throw new Error(`Summary API error: ${res.status}`);
  return res.json() as Promise<SummaryData>;
}

export async function fetchWorldView(): Promise<WorldViewData> {
  const res = await fetch(`${API_BASE}/world-view`);
  if (!res.ok) throw new Error(`WorldView API error: ${res.status}`);
  return res.json() as Promise<WorldViewData>;
}
