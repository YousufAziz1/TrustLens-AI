# TrustLensVerifierV2.1

## Overview & Purpose
`TrustLensVerifierV2_1` is a hardened, substantive Intelligent Contract for decentralized due diligence and project legitimacy verification on the GenLayer network.

It directly evolves from `TrustLensVerifierV2` based on empirical results from real transaction execution on GenLayer Studionet.

---

## Background: Why V2 Returned `INSUFFICIENT_DATA`
In the initial Studionet deployment of `TrustLensVerifierV2` (`0x45306DA83B937fC166c9E45Eb960694f8498E96B`), the verification transaction executed successfully and finalized on-chain:
- **Transaction Outcome**:
  - `verification_state`: `INSUFFICIENT_DATA`
  - `final_decision`: `INSUFFICIENT_DATA`
  - `EXTERNAL_EVIDENCE_ACQUIRED`: HTTP 200
  - `EVIDENCE_COMPARED`: 5 matched, 0 mismatches
- **Adjudication Rationale**:
  The GenLayer consensus LLM evaluated the verified independent evidence and concluded that basic top-level metadata (stars, forks, visibility, and description) **alone was insufficient to verify authentic Web3 project structure, smart contracts, and real source implementation**.

The validators correctly adhered to sound due diligence principles: a repository existing with a public description and stars is **not** sufficient proof that a legitimate decentralized Web3 application or intelligent contract exists.

---

## What V2.1 Independently Verifies
`TrustLensVerifierV2_1` substantially strengthens independent evidence acquisition by querying **four independent GitHub API endpoints** inside cross-validator consensus:

### 1. Repository Metadata Endpoint
- **URL**: `https://api.github.com/repos/{owner}/{repo}`
- **Evidence Acquired**:
  - `exists`: Boolean confirmation of public presence.
  - `owner` & `name`: Canonical repository identity.
  - `is_private`: Visibility status.
  - `default_branch`: Canonical default branch (e.g., `main`).
  - `stars` & `forks`: Community engagement counts.
  - `description`: Bounded project description (up to 200 characters).
  - `has_issues`: Issue tracking status.

### 2. Repository File Tree Endpoint
- **URL**: `https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1`
- **Evidence Acquired**:
  - `has_contracts_dir`: Proves presence of a dedicated `contracts/` directory.
  - `has_frontend_or_src`: Proves presence of user-facing UI or application source (`src/`, `frontend/`, `client/`, `app/`).
  - `has_backend_dir`: Proves presence of backend infrastructure (`backend/`, `server/`, `api/`).
  - `has_package_json`: Proves package configuration manifest.
  - `has_python_manifest`: Proves Python environment configuration (`requirements.txt`, `pyproject.toml`, `Pipfile`).
  - `contract_files_count`: Bounded count of smart/intelligent contract files (`.py`, `.sol`, `.rs`, `.vy`).
  - `source_files_count`: Bounded count of source files (`.ts`, `.tsx`, `.js`, `.py`, `.sol`, `.rs`, `.go`).
  - `test_files_count`: Bounded count of unit/integration test files.

### 3. README Evidence Endpoint
- **URL**: `https://api.github.com/repos/{owner}/{repo}/readme`
- **Evidence Acquired**:
  - `has_readme`: Proves existence of project documentation.
  - `readme_size_bytes`: Quantitative byte size of the README file.
  - `substantive_text`: Boolean indicating whether documentation contains substantive content (>= 200 bytes).
  - `name`: File naming convention (`README.md`).

### 4. Git Activity / Commits Endpoint
- **URL**: `https://api.github.com/repos/{owner}/{repo}/commits?per_page=5`
- **Evidence Acquired**:
  - `has_commits`: Verifies repository contains commit history.
  - `recent_commits_count`: Bounded count of recent commits (capped at 5).
  - `latest_commit_sha`: Truncated 7-character hash of the latest commit for auditability without storing large payloads.

### 5. TrustLens Source Verification
The contract independently inspects the file tree to confirm the presence of TrustLens core components:
- `contracts/TrustLensVerifier.py` (V1 contract)
- `contracts/TrustLensVerifierV2.py` (V2 contract)
- `contracts/TrustLensVerifierV2_README.md` (V2 documentation)
- `contracts/TrustLensVerifierV2_1.py` (V2.1 contract)

### 6. Web3 Architecture Indicators
- `has_intelligent_contract`: Detects GenLayer / Intelligent contract source code.
- `has_web3_lib`: Detects Web3 integration libraries (`genlayer`, `ethers`, `viem`, `web3`, `wagmi`).
- `has_test_suite`: Confirms dedicated test suites exist.

---

## Evidence Normalization & Consensus Equivalence
All independent external evidence is retrieved inside:
```python
normalized_json = gl.eq_principle.strict_eq(fetch_and_normalize_evidence)
```
- **Deterministic Structure**: All dictionary keys are sorted (`sort_keys=True`).
- **Bounded Fields**: Text lengths and file lists are bounded to prevent memory bloat and non-determinism across nodes.
- **Fail-Closed Strategy**: Any network timeout, rate limit (HTTP 403/429), or 5xx server error is normalized to `status != 200`.

---

## Deterministic Factual Comparison (Strictly Before LLM)
Before any subjective LLM evaluation runs, the contract performs deterministic assertions:
1. `exists`: Caller claim vs independent reality.
2. `owner`: Case-insensitive canonical match.
3. `name`: Case-insensitive canonical match.
4. `is_private`: Visibility match.
5. `default_branch`: Branch identifier match.
6. `has_contracts`: Contract presence verification if claimed by caller.

**Conflict Handling**:
If **any** factual conflict is detected:
- Verification state: `MISMATCH`
- Final decision: `DISPUTE`
- The contract **halts immediately** and does not invoke the LLM.

---

## Adjudication & Approval Criteria
Subjective legitimacy evaluation uses:
```python
adjudication_output = gl.eq_principle.prompt_non_comparative(
    get_adjudication_input,
    task=task,
    criteria=criteria,
)
```
- **Inputs**: The LLM receives **strictly verified independent facts** (metadata, tree analysis, README indicators, commit activity, and Web3 indicators).
- **Strict Output Schema**:
  ```json
  {
    "verdict": "APPROVE" | "REJECT" | "INSUFFICIENT_DATA",
    "rationale": "1-2 sentence explanation"
  }
  ```
- **Zero Silent Fallback**: If LLM output fails JSON parsing or provides an invalid verdict, the contract **strictly returns `INSUFFICIENT_DATA`**. It will **never** silently fall back to `APPROVE`.
- **Approval Threshold**: `APPROVE` requires coherent, substantive repository architecture (contracts, documentation, tests, and active commit history). Repository existence alone will never result in `APPROVE`.

---

## Verification Lifecycle
`TrustLensVerifierV2_1` defines 12 discrete lifecycle stages:
1. `RECEIVED`: Submission payload received by contract.
2. `INPUT_VALIDATED`: Target repository format and syntax validated.
3. `EXTERNAL_EVIDENCE_REQUESTED`: Multi-endpoint external fetch initiated.
4. `EXTERNAL_EVIDENCE_ACQUIRED`: HTTP responses obtained from all 4 endpoints.
5. `EVIDENCE_NORMALIZED`: Stable facts extracted and verified across validators.
6. `EVIDENCE_COMPARED`: Caller claims compared against independent facts.
7. `PROJECT_STRUCTURE_ANALYZED`: Objective structural thresholds computed.
8. `ADJUDICATION_RUNNING`: Non-comparative consensus LLM evaluation running.
9. Final Decision Stage:
   - `VERIFIED` (`APPROVE`)
   - `MISMATCH` (`DISPUTE`)
   - `INSUFFICIENT_DATA` (`INSUFFICIENT_DATA`)
   - `REJECTED` (`REJECT`)

---

## Zero Fabricated Telemetry Guarantee
In strict adherence to network truth and submission standards:
```json
"telemetry": {
    "validator_count": null,
    "votes": null,
    "confidence": null,
    "consensus_percentage": null,
    "latency_ms": null
}
```
All consensus telemetry fields remain explicitly `null`. No artificial counts, mock votes, or invented latency figures are ever stored on-chain.

---

## Public Methods
- `@gl.public.write verify_project(submission_json: str) -> str`: Executes the complete verification lifecycle.
- `@gl.public.view get_verification(verification_id: str) -> str`: Fetches a persistent verification record by ID.
- `@gl.public.view get_latest_verification() -> str`: Fetches the most recent verification record.
- `@gl.public.view get_verification_count() -> u32`: Returns the total number of verifications performed.
- `@gl.public.view get_contract_metadata() -> str`: Returns contract specification, version `2.1.0`, and capability metadata.

---

## Limitations & Boundary Conditions
1. **GitHub API Rate Limits**: Public unauthenticated GitHub API requests are limited per IP by GitHub.
2. **Repository Size**: File tree indexing is capped at 500 files to maintain deterministic execution time within GenLayer gas limits.
3. **Private Repositories**: Private repositories cannot be indexed without access tokens; their presence must be verified through authenticated bridges.
