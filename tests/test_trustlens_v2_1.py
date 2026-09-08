"""
Unit Tests for TrustLensVerifierV2_1 Intelligent Contract.

Comprehensive test coverage across all required scenarios:
1. valid submission
2. invalid JSON payload
3. invalid repository format (missing or not owner/repo)
4. successful multi-endpoint independent evidence acquisition
5. GitHub 404 (repository not found => REJECTED)
6. external HTTP failure / network error (=> INSUFFICIENT_DATA, never PASS)
7. normalized repository metadata verification
8. README evidence handling (existence, size, substantive text boolean)
9. repository tree evidence handling (contracts, src, package.json, file counts)
10. TrustLens core source files detection in file tree
11. deterministic factual mismatch detection (triggers MISMATCH / DISPUTE before LLM)
12. insufficient-evidence adjudication (sparse repo or LLM returns INSUFFICIENT_DATA)
13. APPROVE adjudication with sufficiently rich evidence
14. malformed adjudication output (strictly returns INSUFFICIENT_DATA, never silently defaults to APPROVE)
15. zero fabricated telemetry (all validator telemetry metrics are None / null)
16. persistent on-chain record query methods (get_verification, get_latest, get_count, metadata)
"""

import sys
import os
import types
import json
import pytest

# Inject Mock GenVM Runtime Environment for pytest
mock_gl_module = types.ModuleType("genlayer")

class MockContract:
    pass

class MockTreeMap(dict):
    pass

class MockPublic:
    @staticmethod
    def write(fn):
        return fn

    @staticmethod
    def view(fn):
        return fn

class MockWebResponse:
    def __init__(self, status: int, body: bytes):
        self.status = status
        self.body = body

class MockNondetWeb:
    responses = {}
    default_response = MockWebResponse(200, b"{}")

    @classmethod
    def get(cls, url, headers=None):
        if "/git/trees/" in url:
            return cls.responses.get("trees", cls.default_response)
        elif "/readme" in url:
            return cls.responses.get("readme", cls.default_response)
        elif "/commits" in url:
            return cls.responses.get("commits", cls.default_response)
        elif "/repos/" in url:
            return cls.responses.get("repo", cls.default_response)
        return cls.default_response

class MockNondet:
    web = MockNondetWeb

class MockEqPrinciple:
    prompt_return = '{"verdict": "APPROVE", "rationale": "Authentic Web3 project structure verified."}'
    last_eval_input = None

    @classmethod
    def strict_eq(cls, fn):
        return fn()

    @classmethod
    def prompt_non_comparative(cls, get_eval_input, task="", criteria=""):
        cls.last_eval_input = get_eval_input()
        return cls.prompt_return

class MockGL:
    Contract = MockContract
    public = MockPublic
    nondet = MockNondet
    eq_principle = MockEqPrinciple

mock_gl_module.Contract = MockContract
mock_gl_module.TreeMap = MockTreeMap
mock_gl_module.u32 = int
mock_gl_module.gl = MockGL
sys.modules["genlayer"] = mock_gl_module

# Import TrustLensVerifierV2_1
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "contracts"))
from TrustLensVerifierV2_1 import TrustLensVerifierV2_1


@pytest.fixture
def contract():
    return TrustLensVerifierV2_1()


def set_mock_github(repo_data=None, tree_paths=None, readme_data=None, commits_data=None, repo_status=200, tree_status=200, readme_status=200, commits_status=200):
    """Configure mock responses for all 4 GitHub endpoints."""
    MockNondetWeb.responses.clear()

    # 1. Repository metadata endpoint
    if repo_data is None and repo_status == 200:
        repo_data = {
            "owner": {"login": "testorg"},
            "name": "testrepo",
            "private": False,
            "default_branch": "main",
            "stargazers_count": 120,
            "forks_count": 25,
            "description": "Authentic Web3 Intelligent Contract project",
            "has_issues": True,
        }
    repo_body = json.dumps(repo_data or {}).encode("utf-8")
    MockNondetWeb.responses["repo"] = MockWebResponse(repo_status, repo_body)

    # 2. Git tree endpoint
    if tree_paths is None and tree_status == 200:
        tree_paths = [
            "README.md",
            "package.json",
            "tsconfig.json",
            "contracts/TrustLensVerifier.py",
            "contracts/TrustLensVerifierV2.py",
            "contracts/TrustLensVerifierV2_README.md",
            "contracts/TrustLensVerifierV2_1.py",
            "src/lib/genlayer/contract.ts",
            "src/lib/genlayer/client.ts",
            "tests/test_trustlens_v2_1.py",
        ]
    tree_payload = {"tree": [{"path": p, "type": "blob"} for p in (tree_paths or [])]}
    tree_body = json.dumps(tree_payload).encode("utf-8")
    MockNondetWeb.responses["trees"] = MockWebResponse(tree_status, tree_body)

    # 3. README endpoint
    if readme_data is None and readme_status == 200:
        readme_data = {
            "name": "README.md",
            "size": 3500,
            "encoding": "base64",
        }
    readme_body = json.dumps(readme_data or {}).encode("utf-8")
    MockNondetWeb.responses["readme"] = MockWebResponse(readme_status, readme_body)

    # 4. Commits endpoint
    if commits_data is None and commits_status == 200:
        commits_data = [
            {"sha": "abcdef1234567890", "commit": {"message": "feat: release v2.1"}}
        ]
    commits_body = json.dumps(commits_data or []).encode("utf-8")
    MockNondetWeb.responses["commits"] = MockWebResponse(commits_status, commits_body)


# 1. Test: Valid submission and successful verification lifecycle
def test_valid_submission_lifecycle(contract):
    set_mock_github()
    MockEqPrinciple.prompt_return = '{"verdict": "APPROVE", "rationale": "Substantive Web3 architecture verified with contracts and tests."}'

    payload = json.dumps({
        "repository": "testorg/testrepo",
        "caller_claims": {
            "owner": "testorg",
            "name": "testrepo",
            "is_private": False,
            "default_branch": "main",
            "has_contracts": True,
        },
        "subjective_context": "Verifying TrustLens core contracts"
    })

    result_json = contract.verify_project(payload)
    result = json.loads(result_json)

    assert result["verification_state"] == "VERIFIED"
    assert result["final_decision"] == "APPROVE"
    assert result["adjudication"]["verdict"] == "APPROVE"
    assert len(result["stages"]) >= 8

    # Verify stage progression
    stage_names = [s["stage"] for s in result["stages"]]
    assert "RECEIVED" in stage_names
    assert "INPUT_VALIDATED" in stage_names
    assert "EXTERNAL_EVIDENCE_REQUESTED" in stage_names
    assert "EXTERNAL_EVIDENCE_ACQUIRED" in stage_names
    assert "EVIDENCE_NORMALIZED" in stage_names
    assert "EVIDENCE_COMPARED" in stage_names
    assert "PROJECT_STRUCTURE_ANALYZED" in stage_names
    assert "ADJUDICATION_RUNNING" in stage_names
    assert "VERIFIED" in stage_names


# 2. Test: Malformed JSON payload
def test_malformed_json(contract):
    result_json = contract.verify_project("INVALID_JSON{broken")
    result = json.loads(result_json)

    assert result["verification_state"] == "REJECTED"
    assert result["final_decision"] == "REJECT"
    assert "Malformed JSON" in result["comparison_result"]["reason"]


# 3. Test: Invalid repository format (missing or invalid format)
def test_invalid_repository_format(contract):
    result_json = contract.verify_project(json.dumps({"repository": "invalid_single_name"}))
    result = json.loads(result_json)

    assert result["verification_state"] == "REJECTED"
    assert result["final_decision"] == "REJECT"
    assert "owner/repo" in result["adjudication"]["rationale"]


# 4. Test: Multi-endpoint independent evidence acquisition & normalization
def test_multi_endpoint_evidence_normalization(contract):
    set_mock_github()
    MockEqPrinciple.prompt_return = '{"verdict": "APPROVE", "rationale": "Verified"}'

    payload = json.dumps({"repository": "testorg/testrepo"})
    result = json.loads(contract.verify_project(payload))

    ind = result["independent_evidence"]
    assert ind["exists"] is True
    assert ind["owner"] == "testorg"
    assert ind["name"] == "testrepo"
    assert ind["stars"] == 120
    assert ind["forks"] == 25

    # Check tree evidence
    tree_ev = ind["tree_evidence"]
    assert tree_ev["status"] == 200
    assert tree_ev["has_contracts_dir"] is True
    assert tree_ev["has_frontend_or_src"] is True
    assert tree_ev["has_package_json"] is True
    assert tree_ev["contract_files_count"] >= 3

    # Check README evidence
    readme_ev = ind["readme_evidence"]
    assert readme_ev["has_readme"] is True
    assert readme_ev["readme_size_bytes"] == 3500
    assert readme_ev["substantive_text"] is True

    # Check Git commits
    git_ev = ind["git_activity"]
    assert git_ev["has_commits"] is True
    assert git_ev["recent_commits_count"] == 1
    assert git_ev["latest_commit_sha"] == "abcdef1"


# 5. Test: GitHub 404 (repository not found)
def test_repository_not_found_404(contract):
    set_mock_github(repo_status=404)

    payload = json.dumps({"repository": "ghost/nonexistent"})
    result = json.loads(contract.verify_project(payload))

    assert result["verification_state"] == "REJECTED"
    assert result["final_decision"] == "REJECT"
    assert result["independent_evidence"]["status"] == 404
    assert result["independent_evidence"]["exists"] is False


# 6. Test: External HTTP failure / network error (must return INSUFFICIENT_DATA, never PASS)
def test_external_http_failure(contract):
    set_mock_github(repo_status=500)

    payload = json.dumps({"repository": "testorg/testrepo"})
    result = json.loads(contract.verify_project(payload))

    assert result["verification_state"] == "INSUFFICIENT_DATA"
    assert result["final_decision"] == "INSUFFICIENT_DATA"
    assert result["independent_evidence"]["status"] == 500


# 7. Test: Tree endpoint failure (triggers INSUFFICIENT_DATA)
def test_tree_endpoint_failure(contract):
    set_mock_github(tree_status=403)

    payload = json.dumps({"repository": "testorg/testrepo"})
    result = json.loads(contract.verify_project(payload))

    assert result["verification_state"] == "INSUFFICIENT_DATA"
    assert result["final_decision"] == "INSUFFICIENT_DATA"


# 8. Test: README evidence handling (missing vs substantive)
def test_readme_evidence_handling(contract):
    # Test with small non-substantive README (< 200 bytes)
    set_mock_github(readme_data={"name": "README.md", "size": 50})
    MockEqPrinciple.prompt_return = '{"verdict": "APPROVE", "rationale": "Verified"}'

    payload = json.dumps({"repository": "testorg/testrepo"})
    result = json.loads(contract.verify_project(payload))

    readme_ev = result["independent_evidence"]["readme_evidence"]
    assert readme_ev["has_readme"] is True
    assert readme_ev["readme_size_bytes"] == 50
    assert readme_ev["substantive_text"] is False


# 9. Test: TrustLens core source files detection in file tree
def test_trustlens_source_files_detection(contract):
    set_mock_github(tree_paths=[
        "contracts/TrustLensVerifier.py",
        "contracts/TrustLensVerifierV2.py",
        "contracts/TrustLensVerifierV2_README.md",
        "contracts/TrustLensVerifierV2_1.py",
    ])
    MockEqPrinciple.prompt_return = '{"verdict": "APPROVE", "rationale": "Verified"}'

    payload = json.dumps({"repository": "testorg/testrepo"})
    result = json.loads(contract.verify_project(payload))

    tl_files = result["independent_evidence"]["trustlens_files"]
    assert tl_files["has_v1_contract"] is True
    assert tl_files["has_v2_contract"] is True
    assert tl_files["has_v2_readme"] is True
    assert tl_files["has_v2_1_contract"] is True


# 10. Test: Deterministic factual mismatch detection (MISMATCH / DISPUTE before LLM)
def test_factual_mismatch_owner(contract):
    set_mock_github()

    payload = json.dumps({
        "repository": "testorg/testrepo",
        "caller_claims": {
            "owner": "impostor_owner",  # Factual mismatch!
            "name": "testrepo",
        }
    })

    result = json.loads(contract.verify_project(payload))

    assert result["verification_state"] == "MISMATCH"
    assert result["final_decision"] == "DISPUTE"
    assert result["comparison_result"]["matched"] is False
    assert any("Owner mismatch" in m for m in result["comparison_result"]["mismatches"])


def test_factual_mismatch_contracts_claim(contract):
    # Tree has NO contracts
    set_mock_github(tree_paths=["index.html", "style.css"])

    payload = json.dumps({
        "repository": "testorg/testrepo",
        "caller_claims": {
            "owner": "testorg",
            "name": "testrepo",
            "has_contracts": True,  # Factual conflict!
        }
    })

    result = json.loads(contract.verify_project(payload))

    assert result["verification_state"] == "MISMATCH"
    assert result["final_decision"] == "DISPUTE"
    assert any("Contracts dir mismatch" in m for m in result["comparison_result"]["mismatches"])


# 11. Test: Insufficient-evidence adjudication (LLM returns INSUFFICIENT_DATA)
def test_insufficient_data_adjudication(contract):
    set_mock_github()
    MockEqPrinciple.prompt_return = '{"verdict": "INSUFFICIENT_DATA", "rationale": "Project claims require additional contract audit evidence."}'

    payload = json.dumps({"repository": "testorg/testrepo"})
    result = json.loads(contract.verify_project(payload))

    assert result["verification_state"] == "INSUFFICIENT_DATA"
    assert result["final_decision"] == "INSUFFICIENT_DATA"
    assert result["adjudication"]["verdict"] == "INSUFFICIENT_DATA"


# 12. Test: REJECT adjudication
def test_reject_adjudication(contract):
    set_mock_github()
    MockEqPrinciple.prompt_return = '{"verdict": "REJECT", "rationale": "Repository exhibits characteristics of duplicate or malicious scaffolding."}'

    payload = json.dumps({"repository": "testorg/testrepo"})
    result = json.loads(contract.verify_project(payload))

    assert result["verification_state"] == "REJECTED"
    assert result["final_decision"] == "REJECT"
    assert result["adjudication"]["verdict"] == "REJECT"


# 13. Test: Malformed LLM output MUST return INSUFFICIENT_DATA (never silently default to APPROVE!)
def test_malformed_llm_output_never_approves(contract):
    set_mock_github()
    # Unparseable garbled text from LLM
    MockEqPrinciple.prompt_return = "MALFORMED_OUTPUT_NOT_JSON: Congratulations, looks good!"

    payload = json.dumps({"repository": "testorg/testrepo"})
    result = json.loads(contract.verify_project(payload))

    assert result["verification_state"] == "INSUFFICIENT_DATA"
    assert result["final_decision"] == "INSUFFICIENT_DATA"
    assert result["adjudication"]["verdict"] == "INSUFFICIENT_DATA"
    assert "Malformed" in result["adjudication"]["rationale"]


# 14. Test: Zero fabricated telemetry (all telemetry fields strictly None / null)
def test_zero_fabricated_telemetry(contract):
    set_mock_github()
    MockEqPrinciple.prompt_return = '{"verdict": "APPROVE", "rationale": "Authentic"}'

    payload = json.dumps({"repository": "testorg/testrepo"})
    result = json.loads(contract.verify_project(payload))

    telemetry = result["telemetry"]
    assert telemetry["validator_count"] is None
    assert telemetry["votes"] is None
    assert telemetry["confidence"] is None
    assert telemetry["consensus_percentage"] is None
    assert telemetry["latency_ms"] is None


# 15. Test: Persistent storage and view methods
def test_persistent_storage_and_queries(contract):
    set_mock_github()
    MockEqPrinciple.prompt_return = '{"verdict": "APPROVE", "rationale": "Verified"}'

    res1 = contract.verify_project(json.dumps({"repository": "testorg/testrepo"}))
    assert contract.get_verification_count() == 1

    latest = json.loads(contract.get_latest_verification())
    assert latest["verification_id"] == "v_1"

    specific = json.loads(contract.get_verification("v_1"))
    assert specific["verification_id"] == "v_1"
    assert specific["target_repository"] == "testorg/testrepo"

    metadata = json.loads(contract.get_contract_metadata())
    assert metadata["contract"] == "TrustLensVerifierV2_1"
    assert metadata["version"] == "2.1.0"
    assert "multi_endpoint_independent_github_evidence" in metadata["features"]
