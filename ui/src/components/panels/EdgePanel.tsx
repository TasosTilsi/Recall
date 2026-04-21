// EdgePanel — stub for v3.0 (DetailEdge type removed from API)
// Edges in v3.0 use GraphEdge shape (from_id, to_id, relationship) and do not have a detail endpoint.

export function EdgePanel() {
  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-400">
        Edge detail view is not available in v3.0. Relationship data is shown in the Relations table.
      </p>
    </div>
  );
}
