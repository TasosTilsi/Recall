export interface NodeData {
  id: string;
  name: string;
  entityType: string;
  scope: 'project' | 'global';
  summary: string;
  pinned: boolean;
  accessCount: number;
  lastAccessedAt: string;
  createdAt: string;
}

export interface LinkData {
  source: string;
  target: string;
  label: string;
  fact: string;
}

export interface GraphData {
  nodes: NodeData[];
  links: LinkData[];
}

export interface NodeDetail extends NodeData {
  relationships: { name: string; target: string; label: string }[];
}

const API_BASE = '/api';

export async function fetchGraph(scope: 'project' | 'global'): Promise<GraphData> {
  const res = await fetch(`${API_BASE}/graph?scope=${scope}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchNodeDetail(uuid: string): Promise<NodeDetail> {
  const res = await fetch(`${API_BASE}/nodes/${uuid}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
