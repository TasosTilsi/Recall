import type { GraphData, DashboardData, DetailRecord, SearchResults } from '../types/api';

const API_BASE = '/api';

export async function fetchGraph(scope: string): Promise<GraphData> {
  const res = await fetch(`${API_BASE}/graph?scope=${scope}`);
  if (!res.ok) throw new Error(`Graph API error: ${res.status}`);
  return res.json() as Promise<GraphData>;
}

export async function fetchDashboard(scope: string): Promise<DashboardData> {
  const res = await fetch(`${API_BASE}/dashboard?scope=${scope}`);
  if (!res.ok) throw new Error(`Dashboard API error: ${res.status}`);
  return res.json() as Promise<DashboardData>;
}

export async function fetchDetail(itemType: string, itemId: string, scope: string): Promise<DetailRecord> {
  const res = await fetch(`${API_BASE}/detail/${itemType}/${encodeURIComponent(itemId)}?scope=${scope}`);
  if (!res.ok) throw new Error(`Detail API error: ${res.status} for ${itemType}/${itemId}`);
  return res.json() as Promise<DetailRecord>;
}

export async function fetchSearch(q: string, scope: string): Promise<SearchResults> {
  const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(q)}&scope=${scope}`);
  if (!res.ok) throw new Error(`Search API error: ${res.status}`);
  return res.json() as Promise<SearchResults>;
}
