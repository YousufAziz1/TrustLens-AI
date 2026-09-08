# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json


class TrustLensVerifierV2_1(gl.Contract):
    """
    TrustLensVerifierV2_1: Substantive Intelligent Contract for Decentralized Project Due Diligence.

    Evolution from V2:
    - V2 on Studionet finalized with INSUFFICIENT_DATA because top-level metadata alone
      (stars, forks, description) was insufficient for LLM consensus to verify authentic Web3 structure.
    - V2.1 significantly hardens independent evidence acquisition by querying multiple public GitHub endpoints:
      1. Repository Metadata: api.github.com/repos/{owner}/{repo}
      2. Repository File Tree: api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1
      3. README Content/Size: api.github.com/repos/{owner}/{repo}/readme
      4. Recent Git Commits: api.github.com/repos/{owner}/{repo}/commits?per_page=5
      5. TrustLens Source Verification: Independently proves presence of TrustLens contracts & README in the tree.
      6. Web3 Architecture Indicators: Intelligent contracts, frontend/web3 libs, test suite presence.

    Core Security & Integrity Guarantees:
    - Zero caller evidence used as factual truth.
    - Deterministic factual comparison BEFORE subjective LLM adjudication.
    - Any factual conflict triggers MISMATCH / DISPUTE.
    - No network/API failure can ever become PASS.
    - No silent fallback to APPROVE; malformed LLM outputs strictly return INSUFFICIENT_DATA.
    - Zero fabricated telemetry (validator counts, votes, latency remain null).
    """

    verifications: TreeMap[str, str]
    verification_count: u32

    def __init__(self):
        self.verifications = TreeMap()
        self.verification_count = 0

    @gl.public.write
    def verify_project(self, submission_json: str) -> str:
        """
        Execute substantive end-to-end project verification lifecycle:
        Caller Submission -> Input Validation -> Independent Multi-Endpoint Evidence Acquisition
        -> Evidence Normalization -> Deterministic Factual Comparison -> Project Structure Analysis
        -> GenLayer Consensus Adjudication -> State Transition -> Persistent On-Chain Storage.
        """
        stages = []

        def add_stage(stage_name: str, detail: str = ""):
            stages.append({"stage": stage_name, "detail": detail})

        # 1. Stage: RECEIVED
        add_stage("RECEIVED", "Submission payload received by contract")

        # 2. Stage: INPUT_VALIDATED
        try:
            submission = json.loads(submission_json)
        except Exception as e:
            add_stage("REJECTED", f"Malformed JSON payload: {str(e)}")
            return self._store_and_return_record(
                target_repo="unknown",
                verification_state="REJECTED",
                final_decision="REJECT",
                stages=stages,
                caller_evidence={},
                independent_evidence={},
                comparison_result={"matched": False, "reason": "Malformed JSON payload"},
                adjudication={"verdict": "REJECT", "rationale": "Invalid JSON submission payload."},
            )

        # Parse target repository and claims
        target_repo = str(submission.get("repository", "")).strip()
        if not target_repo and "target_url" in submission:
            url = str(submission["target_url"]).strip()
            if "github.com/" in url:
                target_repo = url.split("github.com/")[-1].strip().strip("/")
            else:
                target_repo = url

        # Normalize target repo format (owner/repo)
        if not target_repo or "/" not in target_repo:
            add_stage("REJECTED", "Target repository must be in 'owner/repo' format")
            return self._store_and_return_record(
                target_repo=target_repo or "unknown",
                verification_state="REJECTED",
                final_decision="REJECT",
                stages=stages,
                caller_evidence=submission,
                independent_evidence={},
                comparison_result={"matched": False, "reason": "Missing or invalid repository identifier"},
                adjudication={"verdict": "REJECT", "rationale": "Missing or invalid repository identifier (must be owner/repo)."},
            )

        repo_parts = target_repo.split("/")
        owner = repo_parts[0].strip()
        repo_name = repo_parts[1].strip()
        canonical_repo = f"{owner}/{repo_name}"

        caller_claims = submission.get("caller_claims", {})
        if not caller_claims:
            caller_claims = {
                "exists": True,
                "owner": owner,
                "name": repo_name,
                "is_private": submission.get("is_private", False),
                "default_branch": submission.get("default_branch", "main"),
                "stars": submission.get("repository_metrics", {}).get("stars"),
                "forks": submission.get("repository_metrics", {}).get("forks"),
            }

        subjective_context = str(submission.get("subjective_context", ""))[:300]
        add_stage("INPUT_VALIDATED", f"Target: {canonical_repo}")

        # 3. Stage: EXTERNAL_EVIDENCE_REQUESTED
        add_stage("EXTERNAL_EVIDENCE_REQUESTED", f"Requesting multi-source public GitHub evidence for {canonical_repo}")

        # 4. Independent Evidence Acquisition & Normalization inside gl.eq_principle.strict_eq
        def fetch_and_normalize_evidence() -> str:
            headers = {
                "User-Agent": "GenLayer-TrustLensVerifier/2.1",
                "Accept": "application/vnd.github.v3+json",
            }
            repo_api_url = f"https://api.github.com/repos/{owner}/{repo_name}"

            # Step A: Fetch Repository Metadata
            try:
                res_repo = gl.nondet.web.get(repo_api_url, headers=headers)
                status_code = int(res_repo.status)
            except Exception as ex:
                return json.dumps({"status": 0, "exists": False, "error": f"Metadata fetch exception: {str(ex)}"}, sort_keys=True)

            if status_code == 404:
                return json.dumps({"status": 404, "exists": False, "error": "Not Found"}, sort_keys=True)
            elif status_code != 200:
                return json.dumps({"status": status_code, "exists": False, "error": f"HTTP {status_code}"}, sort_keys=True)

            try:
                repo_data = json.loads(res_repo.body.decode("utf-8"))
            except Exception as ex:
                return json.dumps({"status": 0, "exists": False, "error": f"Metadata parse exception: {str(ex)}"}, sort_keys=True)

            default_branch = str(repo_data.get("default_branch", "main") or "main")

            # Step B: Fetch Repository Tree Evidence
            tree_url = f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/{default_branch}?recursive=1"
            tree_status = 0
            paths = []
            try:
                res_tree = gl.nondet.web.get(tree_url, headers=headers)
                tree_status = int(res_tree.status)
                if tree_status == 200:
                    tree_data = json.loads(res_tree.body.decode("utf-8"))
                    entries = tree_data.get("tree", [])
                    # Extract and normalize paths (lowercase for case-insensitive matching)
                    for item in entries:
                        p = str(item.get("path", "")).strip()
                        if p:
                            paths.append(p)
            except Exception:
                tree_status = 0

            # Step C: Fetch README Evidence
            readme_url = f"https://api.github.com/repos/{owner}/{repo_name}/readme"
            readme_status = 0
            has_readme = False
            readme_size = 0
            readme_name = ""
            try:
                res_readme = gl.nondet.web.get(readme_url, headers=headers)
                readme_status = int(res_readme.status)
                if readme_status == 200:
                    readme_data = json.loads(res_readme.body.decode("utf-8"))
                    has_readme = True
                    readme_size = int(readme_data.get("size", 0))
                    readme_name = str(readme_data.get("name", "README.md"))
            except Exception:
                readme_status = 0

            # Step D: Fetch Git Commits Evidence
            commits_url = f"https://api.github.com/repos/{owner}/{repo_name}/commits?per_page=5"
            commits_status = 0
            has_commits = False
            recent_commits_count = 0
            latest_commit_sha = ""
            try:
                res_commits = gl.nondet.web.get(commits_url, headers=headers)
                commits_status = int(res_commits.status)
                if commits_status == 200:
                    commits_data = json.loads(res_commits.body.decode("utf-8"))
                    if isinstance(commits_data, list):
                        has_commits = len(commits_data) > 0
                        recent_commits_count = min(len(commits_data), 5)
                        if has_commits:
                            latest_commit_sha = str(commits_data[0].get("sha", ""))[:7]
            except Exception:
                commits_status = 0

            # Step E: Substantive Repository Analysis from Tree
            lower_paths = [p.lower() for p in paths]
            has_contracts_dir = any(p.startswith("contracts/") or p == "contracts" for p in lower_paths)
            has_frontend_or_src = any(p.startswith("src/") or p.startswith("frontend/") or p.startswith("client/") or p.startswith("app/") for p in lower_paths)
            has_backend_dir = any(p.startswith("backend/") or p.startswith("server/") or p.startswith("api/") for p in lower_paths)
            has_package_json = "package.json" in lower_paths
            has_python_manifest = any(p in lower_paths for p in ["requirements.txt", "pyproject.toml", "pipfile", "setup.py"])

            contract_files_count = sum(1 for p in lower_paths if p.endswith((".py", ".sol", ".rs", ".vy")) and ("contract" in p or p.startswith("contracts/")))
            source_files_count = sum(1 for p in lower_paths if p.endswith((".ts", ".tsx", ".js", ".jsx", ".py", ".sol", ".rs", ".go")))
            test_files_count = sum(1 for p in lower_paths if "test" in p)

            # TrustLens Specific Source Verification
            has_v1_contract = "contracts/trustlensverifier.py" in lower_paths
            has_v2_contract = "contracts/trustlensverifierv2.py" in lower_paths
            has_v2_readme = "contracts/trustlensverifierv2_readme.md" in lower_paths
            has_v2_1_contract = "contracts/trustlensverifierv2_1.py" in lower_paths

            # Web3 Structure Indicators
            has_intelligent_contract = any("genlayer" in p or (p.startswith("contracts/") and p.endswith(".py")) for p in lower_paths)
            has_web3_lib = any("genlayer" in p or "ethers" in p or "viem" in p or "web3" in p or "wagmi" in p for p in lower_paths) or has_package_json

            # Construct Stable, Deterministic Normalized Evidence
            stable_evidence = {
                "status": 200,
                "exists": True,
                "owner": str(repo_data.get("owner", {}).get("login", "")).lower(),
                "name": str(repo_data.get("name", "")).lower(),
                "is_private": bool(repo_data.get("private", False)),
                "default_branch": default_branch,
                "stars": int(repo_data.get("stargazers_count", 0)),
                "forks": int(repo_data.get("forks_count", 0)),
                "description": str(repo_data.get("description", "") or "")[:200],
                "has_issues": bool(repo_data.get("has_issues", False)),
                # README evidence
                "readme_evidence": {
                    "status": readme_status,
                    "has_readme": has_readme,
                    "readme_size_bytes": readme_size,
                    "substantive_text": readme_size >= 200,
                    "name": readme_name,
                },
                # Tree evidence
                "tree_evidence": {
                    "status": tree_status,
                    "total_files_indexed": min(len(paths), 500),
                    "has_contracts_dir": has_contracts_dir,
                    "has_frontend_or_src": has_frontend_or_src,
                    "has_backend_dir": has_backend_dir,
                    "has_package_json": has_package_json,
                    "has_python_manifest": has_python_manifest,
                    "contract_files_count": contract_files_count,
                    "source_files_count": source_files_count,
                    "test_files_count": test_files_count,
                },
                # TrustLens files verification
                "trustlens_files": {
                    "has_v1_contract": has_v1_contract,
                    "has_v2_contract": has_v2_contract,
                    "has_v2_readme": has_v2_readme,
                    "has_v2_1_contract": has_v2_1_contract,
                },
                # Git activity evidence
                "git_activity": {
                    "status": commits_status,
                    "has_commits": has_commits,
                    "recent_commits_count": recent_commits_count,
                    "latest_commit_sha": latest_commit_sha,
                },
                # Web3 structure indicators
                "web3_indicators": {
                    "has_intelligent_contract": has_intelligent_contract,
                    "has_web3_lib": has_web3_lib,
                    "has_test_suite": test_files_count > 0,
                },
            }
            return json.dumps(stable_evidence, sort_keys=True)

        normalized_json = gl.eq_principle.strict_eq(fetch_and_normalize_evidence)

        # 5. Stage: EXTERNAL_EVIDENCE_ACQUIRED
        try:
            ind_evidence = json.loads(normalized_json)
        except Exception:
            ind_evidence = {"status": 0, "exists": False, "error": "Failed to parse normalized evidence JSON"}

        status = ind_evidence.get("status", 0)
        tree_status = ind_evidence.get("tree_evidence", {}).get("status", 0)
        add_stage("EXTERNAL_EVIDENCE_ACQUIRED", f"Repo HTTP {status}, Tree HTTP {tree_status}")

        if status == 404:
            add_stage("REJECTED", "Repository does not exist on public GitHub (HTTP 404)")
            return self._store_and_return_record(
                target_repo=canonical_repo,
                verification_state="REJECTED",
                final_decision="REJECT",
                stages=stages,
                caller_evidence=caller_claims,
                independent_evidence=ind_evidence,
                comparison_result={"matched": False, "mismatches": ["Repository not found (404)"]},
                adjudication={"verdict": "REJECT", "rationale": "Target repository does not exist on GitHub."},
            )
        elif status != 200 or tree_status != 200:
            # Rule: Never convert network failure into PASS!
            error_msg = ind_evidence.get("error", f"Repo HTTP {status}, Tree HTTP {tree_status}")
            add_stage("INSUFFICIENT_DATA", f"External evidence acquisition incomplete: {error_msg}")
            return self._store_and_return_record(
                target_repo=canonical_repo,
                verification_state="INSUFFICIENT_DATA",
                final_decision="INSUFFICIENT_DATA",
                stages=stages,
                caller_evidence=caller_claims,
                independent_evidence=ind_evidence,
                comparison_result={"matched": False, "reason": "External evidence incomplete or unavailable"},
                adjudication={"verdict": "INSUFFICIENT_DATA", "rationale": f"External evidence endpoint failure: {error_msg}"},
            )

        # 6. Stage: EVIDENCE_NORMALIZED
        add_stage("EVIDENCE_NORMALIZED", "Deterministic multi-endpoint evidence normalized and verified across validators")

        # 7. Stage: EVIDENCE_COMPARED (Deterministic factual checks happen strictly BEFORE LLM)
        mismatches = []
        matches = []

        if caller_claims.get("exists") is False:
            mismatches.append("Caller claimed repo does not exist, but it exists publicly")
        else:
            matches.append("exists: true")

        claim_owner = str(caller_claims.get("owner", "")).lower().strip()
        if claim_owner and claim_owner != ind_evidence.get("owner"):
            mismatches.append(f"Owner mismatch: caller claimed '{claim_owner}', verified '{ind_evidence.get('owner')}'")
        elif claim_owner:
            matches.append(f"owner: '{ind_evidence.get('owner')}'")

        claim_name = str(caller_claims.get("name", "")).lower().strip()
        if claim_name and claim_name != ind_evidence.get("name"):
            mismatches.append(f"Repo name mismatch: caller claimed '{claim_name}', verified '{ind_evidence.get('name')}'")
        elif claim_name:
            matches.append(f"name: '{ind_evidence.get('name')}'")

        if "is_private" in caller_claims:
            claim_private = bool(caller_claims["is_private"])
            if claim_private != ind_evidence.get("is_private"):
                mismatches.append(f"Visibility mismatch: caller claimed is_private={claim_private}, verified={ind_evidence.get('is_private')}")
            else:
                matches.append(f"is_private: {ind_evidence.get('is_private')}")

        if "default_branch" in caller_claims and caller_claims["default_branch"]:
            claim_branch = str(caller_claims["default_branch"]).strip()
            if claim_branch != ind_evidence.get("default_branch"):
                mismatches.append(f"Default branch mismatch: caller claimed '{claim_branch}', verified '{ind_evidence.get('default_branch')}'")
            else:
                matches.append(f"default_branch: '{ind_evidence.get('default_branch')}'")

        # Check explicit caller claims about contracts if provided
        if "has_contracts" in caller_claims:
            claim_contracts = bool(caller_claims["has_contracts"])
            verified_contracts = bool(ind_evidence.get("tree_evidence", {}).get("has_contracts_dir", False))
            if claim_contracts != verified_contracts:
                mismatches.append(f"Contracts dir mismatch: caller claimed {claim_contracts}, verified {verified_contracts}")
            else:
                matches.append(f"has_contracts: {verified_contracts}")

        comparison_result = {
            "matched": len(mismatches) == 0,
            "matches": matches,
            "mismatches": mismatches,
            "volatile_metrics": {
                "caller_stars": caller_claims.get("stars"),
                "verified_stars": ind_evidence.get("stars"),
                "caller_forks": caller_claims.get("forks"),
                "verified_forks": ind_evidence.get("forks"),
            },
        }

        add_stage("EVIDENCE_COMPARED", f"{len(matches)} matched, {len(mismatches)} mismatches")

        # Deterministic check failure leads directly to MISMATCH / DISPUTE before LLM
        if len(mismatches) > 0:
            add_stage("MISMATCH", f"Critical factual conflicts: {'; '.join(mismatches)}")
            return self._store_and_return_record(
                target_repo=canonical_repo,
                verification_state="MISMATCH",
                final_decision="DISPUTE",
                stages=stages,
                caller_evidence=caller_claims,
                independent_evidence=ind_evidence,
                comparison_result=comparison_result,
                adjudication={"verdict": "DISPUTE", "rationale": f"Deterministic factual checks failed with {len(mismatches)} conflicts: {'; '.join(mismatches)}"},
            )

        # 8. Stage: PROJECT_STRUCTURE_ANALYZED
        tree_ev = ind_evidence.get("tree_evidence", {})
        readme_ev = ind_evidence.get("readme_evidence", {})
        git_ev = ind_evidence.get("git_activity", {})
        tl_ev = ind_evidence.get("trustlens_files", {})
        web3_ev = ind_evidence.get("web3_indicators", {})

        total_files = tree_ev.get("total_files_indexed", 0)
        contracts_count = tree_ev.get("contract_files_count", 0)
        source_count = tree_ev.get("source_files_count", 0)
        readme_size = readme_ev.get("readme_size_bytes", 0)
        commits_count = git_ev.get("recent_commits_count", 0)

        structure_detail = (
            f"Files: {total_files}, Contracts: {contracts_count}, Sources: {source_count}, "
            f"README: {readme_size}B, Commits: {commits_count}"
        )
        add_stage("PROJECT_STRUCTURE_ANALYZED", structure_detail)

        # 9. Stage: ADJUDICATION_RUNNING
        add_stage("ADJUDICATION_RUNNING", "Executing GenLayer prompt_non_comparative on substantive independent facts")

        def get_adjudication_input() -> str:
            return (
                f"Repository: {canonical_repo}\n"
                f"Verified Repository Facts:\n"
                f"- Visibility: {'Private' if ind_evidence.get('is_private') else 'Public'}, DefaultBranch: {ind_evidence.get('default_branch')}\n"
                f"- Description: {ind_evidence.get('description')}\n"
                f"- Stars: {ind_evidence.get('stars')}, Forks: {ind_evidence.get('forks')}, Issues: {ind_evidence.get('has_issues')}\n"
                f"- README: Exists={readme_ev.get('has_readme')}, SizeBytes={readme_ev.get('readme_size_bytes')}, SubstantiveText={readme_ev.get('substantive_text')}\n"
                f"- File Tree: TotalFiles={total_files}, ContractsDir={tree_ev.get('has_contracts_dir')}, FrontendOrSrc={tree_ev.get('has_frontend_or_src')}, BackendDir={tree_ev.get('has_backend_dir')}\n"
                f"- Manifests: PackageJson={tree_ev.get('has_package_json')}, PythonManifest={tree_ev.get('has_python_manifest')}\n"
                f"- Source Code Metrics: ContractFilesCount={contracts_count}, SourceFilesCount={source_count}, TestFilesCount={tree_ev.get('test_files_count')}\n"
                f"- TrustLens Core Files: V1={tl_ev.get('has_v1_contract')}, V2={tl_ev.get('has_v2_contract')}, V2Readme={tl_ev.get('has_v2_readme')}\n"
                f"- Git Activity: HasCommits={git_ev.get('has_commits')}, RecentCommitsCount={commits_count}\n"
                f"- Web3 Indicators: IntelligentContractSource={web3_ev.get('has_intelligent_contract')}, Web3Libraries={web3_ev.get('has_web3_lib')}, TestSuite={web3_ev.get('has_test_suite')}\n"
                f"Context note: {subjective_context}\n"
                "Evaluate whether this repository exhibits a coherent, authentic Web3 project structure based strictly on verified independent evidence."
            )

        task = (
            "Evaluate repository legitimacy and architectural authenticity based strictly on verified independent facts. "
            "Approval criteria: APPROVE only if the repository demonstrates substantive Web3 project structure, including contracts, documentation, source code, and git activity. "
            "Repository existence or public metadata alone is NEVER sufficient for approval. "
            "If evidence is sparse, missing contracts, or inconclusive, output INSUFFICIENT_DATA. "
            "If evidence shows deceptive or fabricated project structure, output REJECT. "
            "Output valid JSON with exactly two fields: 'verdict' (APPROVE, REJECT, or INSUFFICIENT_DATA) and 'rationale' (concise 1-2 sentence explanation)."
        )

        criteria = (
            "The output must be a valid JSON object with keys 'verdict' and 'rationale'. "
            "The verdict field must strictly be one of: APPROVE, REJECT, INSUFFICIENT_DATA. "
            "Any malformed or invalid JSON is treated as an invalid evaluation."
        )

        adjudication_output = gl.eq_principle.prompt_non_comparative(
            get_adjudication_input,
            task=task,
            criteria=criteria,
        )

        adjudication_parsed = self._parse_adjudication(adjudication_output)
        verdict = str(adjudication_parsed.get("verdict", "INSUFFICIENT_DATA")).upper()

        if verdict == "APPROVE":
            v_state = "VERIFIED"
            f_decision = "APPROVE"
        elif verdict == "REJECT":
            v_state = "REJECTED"
            f_decision = "REJECT"
        else:
            v_state = "INSUFFICIENT_DATA"
            f_decision = "INSUFFICIENT_DATA"

        add_stage(v_state, f"Adjudication completed with verdict: {f_decision}")

        return self._store_and_return_record(
            target_repo=canonical_repo,
            verification_state=v_state,
            final_decision=f_decision,
            stages=stages,
            caller_evidence=caller_claims,
            independent_evidence=ind_evidence,
            comparison_result=comparison_result,
            adjudication=adjudication_parsed,
        )

    @gl.public.view
    def get_latest_verification(self) -> str:
        """Return the most recent verification record as JSON."""
        return self.verifications.get("latest", "{}")

    @gl.public.view
    def get_verification(self, verification_id: str) -> str:
        """Return a specific verification record by ID."""
        return self.verifications.get(verification_id, "{}")

    @gl.public.view
    def get_verification_count(self) -> u32:
        """Return the total number of verifications performed."""
        return self.verification_count

    @gl.public.view
    def get_contract_metadata(self) -> str:
        """Return contract specification and version metadata."""
        return json.dumps({
            "contract": "TrustLensVerifierV2_1",
            "version": "2.1.0",
            "purpose": "Substantive Decentralized Project Due Diligence Verifier",
            "features": [
                "multi_endpoint_independent_github_evidence",
                "repository_tree_and_manifest_indexing",
                "readme_substance_verification",
                "trustlens_source_confirmation",
                "deterministic_pre_adjudication_comparison",
                "non_comparative_consensus_adjudication",
                "no_silent_approve_fallback",
                "zero_fabricated_telemetry",
            ],
            "total_verifications": self.verification_count,
        })

    def _store_and_return_record(
        self,
        target_repo: str,
        verification_state: str,
        final_decision: str,
        stages: list,
        caller_evidence: dict,
        independent_evidence: dict,
        comparison_result: dict,
        adjudication: dict,
    ) -> str:
        """Persist the complete verification record on-chain and return JSON."""
        self.verification_count += 1
        verification_id = f"v_{self.verification_count}"

        record = {
            "verification_id": verification_id,
            "target_repository": target_repo,
            "verification_state": verification_state,
            "final_decision": final_decision,
            "stages": stages,
            "caller_evidence": caller_evidence,
            "independent_evidence": independent_evidence,
            "comparison_result": comparison_result,
            "adjudication": adjudication,
            # Strict compliance: Zero fabricated telemetry.
            "telemetry": {
                "validator_count": None,
                "votes": None,
                "confidence": None,
                "consensus_percentage": None,
                "latency_ms": None,
            },
        }

        serialized = json.dumps(record)
        self.verifications[verification_id] = serialized
        self.verifications["latest"] = serialized
        return serialized

    def _parse_adjudication(self, raw_output) -> dict:
        """
        Safely parse LLM adjudication output into structured verdict and rationale.
        CRITICAL RULE: If parsing fails or output is malformed, NEVER silently default to APPROVE!
        Strictly return INSUFFICIENT_DATA.
        """
        try:
            if isinstance(raw_output, dict):
                verdict = str(raw_output.get("verdict", "")).upper()
                if verdict in ["APPROVE", "REJECT", "INSUFFICIENT_DATA"]:
                    return {"verdict": verdict, "rationale": str(raw_output.get("rationale", ""))}
                return {"verdict": "INSUFFICIENT_DATA", "rationale": f"Unrecognized adjudication verdict: {verdict}"}

            text = str(raw_output).strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1]
                text = text.rsplit("```", 1)[0].strip()
            parsed = json.loads(text)
            if isinstance(parsed, dict) and "verdict" in parsed:
                verdict = str(parsed["verdict"]).upper()
                if verdict in ["APPROVE", "REJECT", "INSUFFICIENT_DATA"]:
                    return {"verdict": verdict, "rationale": str(parsed.get("rationale", ""))}
            return {"verdict": "INSUFFICIENT_DATA", "rationale": "Adjudication JSON did not contain a valid verdict."}
        except Exception as ex:
            # Rule: Malformed output MUST return INSUFFICIENT_DATA, NEVER APPROVE!
            return {"verdict": "INSUFFICIENT_DATA", "rationale": f"Malformed adjudication output: {str(ex)}"}
