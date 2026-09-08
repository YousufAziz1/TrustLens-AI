# TrustLensVerifierV2

## Purpose & Overview
`TrustLensVerifierV2` is a second-generation GenLayer Intelligent Contract designed for decentralized, trustless due diligence verification of Web3 repositories and open-source project claims.

### Rejection Resolution Context
The initial `TrustLensVerifier` submission was rejected due to:
1. Studio link not exposing raw contract source code for independent inspection.
2. Complete reliance on caller-supplied Web3 claims without independent corroboration.
3. An insufficiently substantive verification lifecycle.

`TrustLensVerifierV2` resolves all three points:
- **Publicly Accessible Source**: Committed to GitHub at `https://github.com/YousufAziz1/jinni-agent/blob/main/contracts/TrustLensVerifierV2.py` for full auditability.
- **Independent Public Evidence**: Directly queries GitHub REST APIs via GenLayer's non-deterministic web access (`gl.nondet.web.get`) and reaches validator consensus using the Equivalence Principle (`gl.eq_principle.strict_eq`).
- **Normalized Cross-Validator Consensus**: Strips ephemeral headers and normalizes only stable, objective facts before strict cross-validator consensus.
- **Deterministic-First Comparison**: Cross-checks caller claims against independently acquired facts before any LLM adjudication.
- **Substantive 11-Stage Lifecycle**: Full state traceability with persistent on-chain storage.
- **Zero Fabricated Telemetry**: Validator counts, votes, confidence scores, and latencies remain strictly null/unmodified if not natively exposed by GenVM.

---

## Contract Interface & Methods

### Write Methods
- `verify_project(submission_json: str) -> str`: Accepts project claims, executes external independent evidence retrieval, deterministic comparison, GenLayer non-comparative consensus adjudication, and records the result on-chain.

### Read/View Methods
- `get_latest_verification() -> str`: Returns the latest complete verification record as JSON.
- `get_verification(verification_id: str) -> str`: Returns a specific record by ID (e.g., `"v_1"`).
- `get_verification_count() -> u32`: Returns total verifications executed.

---

## Input Specification
The caller supplies a JSON string payload to `verify_project`:

```json
{
  "repository": "owner/repo",
  "caller_claims": {
    "exists": true,
    "owner": "owner",
    "name": "repo",
    "is_private": false,
    "default_branch": "main",
    "stars": 120,
    "forks": 15
  },
  "subjective_context": "Optional context regarding project roadmap or security audit history"
}
```

Legacy formats containing `target_url` (e.g. `https://github.com/owner/repo`) and nested `repository_metrics` are also automatically parsed and normalized for backwards compatibility.

---

## Independent Evidence Sources
The contract independently queries the official GitHub REST API:
- Endpoint: `https://api.github.com/repos/{owner}/{repo}`
- Headers: `User-Agent: GenLayer-TrustLensVerifier/2.0`, `Accept: application/vnd.github.v3+json`
- Access Mechanism: GenVM non-deterministic web get (`gl.nondet.web.get`) wrapped inside `gl.eq_principle.strict_eq`.

### Extracted Objective Facts
Only stable, objective facts are extracted to ensure deterministic consensus across validators:
- `exists` (boolean)
- `owner` (normalized lowercase string)
- `name` (normalized lowercase string)
- `is_private` (boolean visibility)
- `default_branch` (string)
- `stars` (integer stargazers count)
- `forks` (integer forks count)
- `description` (truncated string)
- `has_issues` (boolean)

---

## Verification Lifecycle
The contract moves through explicit, recorded lifecycle stages:

```
[1] RECEIVED
      │
[2] INPUT_VALIDATED
      │
[3] EXTERNAL_EVIDENCE_REQUESTED
      │
[4] EXTERNAL_EVIDENCE_ACQUIRED
      │
[5] EVIDENCE_NORMALIZED
      │
[6] EVIDENCE_COMPARED
      │
      ├──> (Factual conflict detected) ─────────> [MISMATCH / DISPUTE]
      │
[7] ADJUDICATION_RUNNING
      │
      └──> (GenLayer prompt_non_comparative) ───> [VERIFIED / APPROVE]
                                              └──> [REJECTED / REJECT]
                                              └──> [INSUFFICIENT_DATA]
```

### Discrete Stages
1. `RECEIVED`: Payload received.
2. `INPUT_VALIDATED`: JSON parsed; repo format confirmed.
3. `EXTERNAL_EVIDENCE_REQUESTED`: Public API request prepared.
4. `EXTERNAL_EVIDENCE_ACQUIRED`: Cross-validator web consensus returned.
5. `EVIDENCE_NORMALIZED`: Stable facts isolated.
6. `EVIDENCE_COMPARED`: Caller claims cross-checked against independent facts.
7. `ADJUDICATION_RUNNING`: Non-comparative LLM consensus evaluates verified facts.
8. Terminal States:
   - `VERIFIED`: Claims corroborated and adjudication approved.
   - `MISMATCH`: Direct contradiction between caller claims and independent evidence.
   - `INSUFFICIENT_DATA`: External API unreachable or rate-limited.
   - `REJECTED`: Repo not found (404), invalid input, or failed adjudication.

---

## Decision States & Storage Model

| Verification State | Final Decision | Meaning |
| :--- | :--- | :--- |
| `VERIFIED` | `APPROVE` | Repository exists, claims match independent facts, and adjudication passes. |
| `MISMATCH` | `DISPUTE` | Factual conflict between caller claims and verified facts. |
| `INSUFFICIENT_DATA` | `INSUFFICIENT_DATA` | External API unavailable (network error or 5xx). Never treated as PASS. |
| `REJECTED` | `REJECT` | Repository 404, invalid payload, or failed evaluation. |

### Persistent On-Chain Record Structure
```json
{
  "verification_id": "v_1",
  "target_repository": "owner/repo",
  "verification_state": "VERIFIED",
  "final_decision": "APPROVE",
  "stages": [
    {"stage": "RECEIVED", "detail": "Submission payload received by contract"},
    {"stage": "INPUT_VALIDATED", "detail": "Target: owner/repo"},
    {"stage": "EXTERNAL_EVIDENCE_REQUESTED", "detail": "Requesting public GitHub data"},
    {"stage": "EXTERNAL_EVIDENCE_ACQUIRED", "detail": "HTTP Status: 200"},
    {"stage": "EVIDENCE_NORMALIZED", "detail": "Stable objective facts verified across validators"},
    {"stage": "EVIDENCE_COMPARED", "detail": "4 matched, 0 mismatches"},
    {"stage": "ADJUDICATION_RUNNING", "detail": "Running GenLayer prompt_non_comparative"},
    {"stage": "VERIFIED", "detail": "Adjudication completed with verdict: APPROVE"}
  ],
  "caller_evidence": { ... },
  "independent_evidence": { ... },
  "comparison_result": { "matched": true, "matches": [...], "mismatches": [] },
  "adjudication": { "verdict": "APPROVE", "rationale": "..." },
  "telemetry": {
    "validator_count": null,
    "votes": null,
    "confidence": null,
    "consensus_percentage": null,
    "latency_ms": null
  }
}
```

---

## Deployment Instructions

### Studio Deployment (Recommended)
1. Open [GenLayer Studio](https://studio.genlayer.com).
2. Connect your wallet to **Studionet** (Chain ID: 61999).
3. Create a new contract file named `TrustLensVerifierV2.py`.
4. Copy the complete source code from `contracts/TrustLensVerifierV2.py`.
5. Studio will automatically parse the schema and detect `TrustLensVerifierV2` with zero constructor arguments.
6. Click **Deploy**.
7. Capture the new deployed contract address and transaction hash.

---

## Limitations
1. **GitHub Unauthenticated Rate Limits**: Public calls without an API token are limited by GitHub's IP rate-limiting policy (60 requests/hour/IP). In the event of rate-limiting, the contract securely fails to `INSUFFICIENT_DATA` rather than falsely passing.
2. **Private Repositories**: Cannot be independently verified without authenticated OAuth credentials. Such attempts receive `REJECTED` (404 Not Found) or `INSUFFICIENT_DATA`.
3. **Volatile Metrics**: GitHub stars and forks may change slightly between caller inspection and validator fetching; the comparison layer treats minor variances as non-fatal while strictly checking identity facts (owner, name, default branch, visibility).
