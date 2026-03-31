// Retention badge type
export type RetentionStatus = 'Pinned' | 'Normal' | 'Stale' | 'Archived';

// GraphData — /api/graph response
export interface GraphNode {
  id: string;
  label: string;
  type: string;
  scope: string;
  retention_status?: RetentionStatus;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  name: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// DashboardData — /api/dashboard response
export interface DashboardCounts {
  entities: number;
  edges: number;
  episodes: number;
  deltas: {
    entities_7d: number;
    edges_7d: number;
    episodes_7d: number;
  };
}

export interface TimeSeriesPoint {
  day: string;
  entity_count: number;
  edge_count: number;
  episode_count: number;
}

export interface TopEntity {
  uuid: string;
  name: string;
  edge_count: number;
}

export interface RetentionSummary {
  pinned: number;
  normal: number;
  stale: number;
  archived: number;
}

export interface EpisodeSummary {
  uuid: string;
  name: string;
  source_description: string;
  created_at: string;
  source: string;
  content?: string;
}

export interface DashboardData {
  counts: DashboardCounts;
  time_series: TimeSeriesPoint[];
  top_entities: TopEntity[];
  sources: Record<string, number>;
  entity_types: Record<string, number>;
  retention: RetentionSummary;
  recent_episodes: EpisodeSummary[];
}

// Detail panel types — /api/detail/:type/:id response
export interface EntityRelationship {
  source: string;
  target: string;
  label: string;
  fact: string;
}

export interface DetailEntity {
  uuid: string;
  name: string;
  tags: string[];
  summary: string;
  created_at: string;
  last_accessed_at?: string;
  access_count?: number;
  pinned?: boolean;
  relationships?: EntityRelationship[];
}

export interface DetailEpisode {
  uuid: string;
  name: string;
  source_description: string;
  content: string;
  created_at: string;
  source: string;
  entities: { uuid: string; name: string; tags: string[] }[];
}

export interface DetailEdge {
  source: string;
  target: string;
  label: string;
  fact: string;
}

export type DetailRecord = DetailEntity | DetailEpisode | DetailEdge;

// SearchResults — /api/search response
export interface SearchEntityResult {
  id: string;
  label: string;
  type: string;
  summary: string;
}

export interface SearchRelationResult {
  id: string;
  source: string;
  target: string;
  fact: string;
  label: string;
}

export interface SearchResults {
  entities: SearchEntityResult[];
  relations: SearchRelationResult[];
  episodes: EpisodeSummary[];
}
