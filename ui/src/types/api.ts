// v3.0 API types — six canonical entity types, no episodes, no retention

export type CanonicalEntityType =
  | 'decision'
  | 'bug_fix'
  | 'pattern'
  | 'file'
  | 'concept'
  | 'tech_debt';

// GraphData — /api/graph response
export interface GraphNode {
  id: string;
  label: string;
  type: CanonicalEntityType | string;
  commit_sha: string;
}

export interface GraphEdge {
  id: string;
  from_id: string;
  to_id: string;
  relationship: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// DashboardData — /api/dashboard response
export interface TopEntity {
  id: string;
  name: string;
  type: string;
  backlink_count: number;
}

export interface RecentCommit {
  sha: string;
  message: string;
  author: string;
  date: string;
}

export interface DashboardData {
  total_entities: number;
  total_commits: number;
  entity_types: Record<string, number>;
  top_entities: TopEntity[];
  recent_commits: RecentCommit[];
}

// DetailEntityV3 — /api/detail/entity/{id} response
export interface Backlink {
  from_id: string;
  from_name: string;
  to_id: string;
  relationship: string;
  context: string;
}

export interface DetailEntityV3 {
  id: string;
  name: string;
  type: CanonicalEntityType | string;
  content: string;
  tags: string[];
  commit_sha: string;
  created_at: string;
  backlinks: Backlink[];
}

// SearchResults — /api/search response
export interface SearchEntityResult {
  id: string;
  name: string;
  type: string;
  content_snippet: string;
}

export interface SearchResults {
  entities: SearchEntityResult[];
}
