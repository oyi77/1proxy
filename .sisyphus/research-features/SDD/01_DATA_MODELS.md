# DATA MODELS SPECIFICATION

**Module:** Hunter / Data Layer  
**Focus:** Database Schema for Candidate Sources

---

## 1. CONCEPT: "CANDIDATE SOURCE"
A `CandidateSource` is a URL that *might* contain proxies. It is distinct from a `Source` (which is a trusted, verified provider). Candidates are ephemeral; they either graduate to `Source` or are discarded.

## 2. SCHEMA DEFINITION

### Table: `candidate_sources`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | Primary Key | Unique ID |
| `url` | String | Unique, Index | The raw URL of the file/page |
| `domain` | String | Index | e.g., "github.com", "pastebin.com" |
| `discovery_method` | String | Not Null | Enum: `github`, `search`, `ai`, `manual` |
| `status` | String | Default: `pending` | Enum: `pending`, `validating`, `approved`, `rejected` |
| `confidence_score` | Integer | Default: 0 | 0-100 score based on heuristic analysis |
| `proxies_found_count`| Integer | Default: 0 | Number of unique proxies extracted in last check |
| `last_checked_at` | DateTime | Nullable | Timestamp of last scrape attempt |
| `created_at` | DateTime | Default: UTC Now | Discovery time |
| `metadata` | JSON | Nullable | Store extra info (AI summary, specific commit hash) |

## 3. RELATIONSHIPS
- **None.** This table is intentionally decoupled from `users` and `sources` to allow for easy cleanup of junk data.
- **Promotion:** When "Approved", a new row is created in the `sources` table, and the `candidate_sources` row is marked `approved` (or deleted).

## 4. INDEXING STRATEGY
- `ix_candidate_sources_url`: Fast lookups to prevent re-discovering the same URL.
- `ix_candidate_sources_status`: Fast filtering for "Pending" items in Admin UI.
- `ix_candidate_sources_confidence`: Ordering candidates by promise.
