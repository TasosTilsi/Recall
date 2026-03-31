# Phase 20: TOON Encoding for <relevant_history> Block

## Goal
Implement TOON encoding for the `<relevant_history>` block in `inject_context.py` to achieve ~40% token reduction while maintaining backward compatibility for small history sets.

## Files to Modify
- `src/hooks/inject_context.py`

## Key Changes

### 1. Import Required Functions
Add import for `trim_to_token_budget` from `toon_utils`:
```python
from src.mcp_server.toon_utils import trim_to_token_budget
```

### 2. Preprocessing Function
Add helper function to preprocess snippets for TOON safety:
```python
def _preprocess_for_toon(text: str) -> str:
    """Remove commas and newlines that could break TOON parsing."""
    if not text:
        return ""
    # Replace commas and newlines with spaces
    return text.replace(",", " ").replace("\n", " ").strip()
```

### 3. Modified History Processing Logic
Update the `_build_option_c` function to conditionally use TOON encoding:

```python
def _build_option_c(continuity: str, history_items: list, token_budget: int) -> str:
    """Build Option C XML block within token budget with optional TOON encoding.
    
    Priority when tight: recent session facts -> recent git facts -> older facts (already sorted).
    Uses TOON encoding for history blocks with 3+ items to save ~40% tokens.
    """
    used_tokens = 0

    # Continuity block (fixed cost)
    if continuity:
        continuity_block = f"<continuity>Last session: {continuity}</continuity>"
    else:
        continuity_block = "<continuity></continuity>"
    used_tokens += _approx_tokens(continuity_block)

    # Build relevant_history items within remaining budget
    history_overhead = _approx_tokens("<relevant_history>\n</relevant_history>")
    remaining = token_budget - used_tokens - history_overhead

    # Process history items for TOON encoding (3+ items) or regular format (0-2 items)
    if len(history_items) >= 3:
        # Prepare data for TOON encoding: [snippet, date_str] tuples
        toon_data = []
        for item in history_items:
            snippet = _preprocess_for_toon(
                item.get("snippet", item.get("name", ""))[:300]
            )
            date_str = _format_created_at(item.get("created_at", ""))
            toon_data.append([snippet, date_str])
        
        # Convert to TOON format
        toon_text = encode(toon_data)  # Import encode from toon_utils or toon directly
        
        # Apply token budget trimming to TOON text
        trimmed_toon = trim_to_token_budget(toon_text, remaining)
        
        # Wrap in XML tags
        history_block = f"<relevant_history>\n{trimmed_toon}\n</relevant_history>"
    else:
        # Original format for 0-2 items to avoid TOON overhead
        history_lines = []
        for item in history_items:
            snippet = item.get("snippet", item.get("name", ""))[:300]
            date_str = _format_created_at(item.get("created_at", ""))
            line = f"  - {snippet} (since {date_str}, current)"
            line_tokens = _approx_tokens(line)
            if remaining - line_tokens < 0:
                break
            history_lines.append(line)
            remaining -= line_tokens

        history_block = "<relevant_history>\n" + "\n".join(history_lines) + "\n</relevant_history>"

    return (
        "<session_context>\n"
        + continuity_block + "\n"
        + history_block + "\n"
        + "</session_context>"
    )
```

### 4. Additional Import
Add the `encode` function import:
```python
from toon import encode
```

## Dependencies
- toon library (already installed via toon_utils usage)
- No new dependencies required

## Risks and Mitigations
1. **TOON format breaking due to special characters**
   - Mitigation: Preprocess snippets to remove commas and newlines
   
2. **Backward compatibility for small history sets**
   - Mitigation: Only use TOON for 3+ items, keep original format for 0-2 items
   
3. **Token budget calculation accuracy**
   - Mitigation: Use existing `_approx_tokens` function and `trim_to_token_budget` utility

## Verification Plan
1. **Unit Tests**
   - Test TOON encoding with 3+ history items
   - Test original format preservation with 0-2 items
   - Test token budget enforcement with TOON encoding
   - Test preprocessing function with various inputs
   
2. **Manual Verification**
   - Measure token reduction with sample history data
   - Verify output format correctness
   - Ensure existing functionality remains intact
   
3. **Integration Testing**
   - Run existing test suite to ensure no regressions
   - Test with actual hook invocation scenarios

## Implementation Notes
- The TOON header overhead is justified at 3+ items based on research
- For 0-2 items, JSON format is more efficient than TOON due to header overhead
- Token budget calculation excludes XML tags as specified
- The approach maintains the existing priority ordering of history items