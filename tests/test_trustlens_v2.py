"""
Unit Tests for TrustLensVerifierV2 Intelligent Contract.

Covers all 11 required scenarios:
1. repository exists
2. repository missing (404)
3. caller evidence matches independent evidence
4. caller evidence conflicts with independent evidence
5. external evidence unavailable (500 / network error)
6. malformed submission (invalid JSON)
7. insufficient evidence (missing target)
8. verification record persistence (storage & retrieval)
9. deterministic checks before LLM adjudication
10. unavailable data never becomes PASS
11. no fabricated telemetry
"""

import sys
import os
import types
import json
import pytest

# Inject Mock GenVM Runtime Environment for standard pytest execution
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
    current_response = MockWebResponse(200, b"{}")

    @classmethod
    def get(cls, url, headers=None):
        return cls.current_response

class MockNondet:
    web = MockNondetWeb

class MockEqPrinciple:
    prompt_return = '{"verdict": "APPROVE", "rationale": "Authentic project"}'
    last_eval_input = None

    @classmethod
    def strict_eq(cls, fn):
        # Executes the validator normalization function
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

# Now import TrustLensVerifierV2
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "contracts"))
from TrustLensVerifierV2 import TrustLensVerifierV2


@pytest.fixture
def contract():
    return TrustLensVerifierV2()


def set_github_mock(status: int, data: dict):
    body = json.dumps(data).encode("utf-8")
    MockNondetWeb.current_response = MockWebResponse(status, body)


# 1. Test: repository exists
def test_repository_exists(contract):
    set_github_mock(200, {
        "owner": {"login": "testorg"},
        "name": "testrepo",
        "private": False,
        "default_branch": "main",
        "stargazers_count": 42,
        "forks_count": 8,
        "description": "A verified test repo",
        "has_issues": True
    })
    MockEqPrinciple.prompt_return = '{"verdict": "APPROVE", "rationale": "Authentic"}'

    payload = json.dumps({
        "repository": "testorg/testrepo",
        "caller_claims": {
            "owner": "testorg",
            "name": "testrepo",
            "is_private": False,
            "default_branch": "main",
            "stars": 42
        }
    })

    result_json = contract.verify_project(payload)
    result = json.loads(result_json)

    assert result["verification_state"] == "VERIFIED"
    assert result["final_decision"] == "APPROVE"
    assert result["independent_evidence"]["exists"] is True
    assert result["independent_evidence"]["owner"] == "testorg"
    assert result["independent_evidence"]["name"] == "testrepo"


# 2. Test: repository missing (404)
def test_repository_missing_404(contract):
    set_github_mock(404, {"message": "Not Found"})

    payload = json.dumps({
        "repository": "ghost/nonexistent",
        "caller_claims": {"owner": "ghost", "name": "nonexistent"}
    })

    result_json = contract.verify_project(payload)
    result = json.loads(result_json)

    assert result["verification_state"] == "REJECTED"
    assert result["final_decision"] == "REJECT"
    assert result["independent_evidence"]["status"] == 404
    assert result["independent_evidence"]["exists"] is False
    assert any("404" in stage["detail"] for stage in result["stages"])


# 3. Test: caller evidence matches independent evidence
def test_caller_evidence_matches_independent(contract):
    set_github_mock(200, {
        "owner": {"login": "alice"},
        "name": "superapp",
        "private": False,
        "default_branch": "main",
        "stargazers_count": 100,
        "forks_count": 20,
        "description": "Valid dapp"
    })
    MockEqPrinciple.prompt_return = '{"verdict": "APPROVE", "rationale": "High quality Web3 dapp"}'

    payload = json.dumps({
        "repository": "alice/superapp",
        "caller_claims": {
            "owner": "alice",
            "name": "superapp",
            "is_private": False,
            "default_branch": "main"
        }
    })

    result_json = contract.verify_project(payload)
    result = json.loads(result_json)

    assert result["comparison_result"]["matched"] is True
    assert len(result["comparison_result"]["mismatches"]) == 0
    assert result["verification_state"] == "VERIFIED"


# 4. Test: caller evidence conflicts with independent evidence
def test_caller_evidence_conflicts(contract):
    set_github_mock(200, {
        "owner": {"login": "realowner"},
        "name": "publicrepo",
        "private": False,
        "default_branch": "main",
        "stargazers_count": 5,
        "forks_count": 1
    })

    # Caller falsely claims repo is private and owned by impostor
    payload = json.dumps({
        "repository": "realowner/publicrepo",
        "caller_claims": {
            "owner": "impostor",
            "name": "publicrepo",
            "is_private": True,
            "default_branch": "develop"
        }
    })

    result_json = contract.verify_project(payload)
    result = json.loads(result_json)

    assert result["verification_state"] == "MISMATCH"
    assert result["final_decision"] == "DISPUTE"
    assert result["comparison_result"]["matched"] is False
    assert len(result["comparison_result"]["mismatches"]) >= 2
    # Verify conflicts recorded
    mismatches_str = " ".join(result["comparison_result"]["mismatches"])
    assert "impostor" in mismatches_str
    assert "Visibility mismatch" in mismatches_str


# 5. Test: external evidence unavailable (500)
def test_external_evidence_unavailable_500(contract):
    set_github_mock(500, {"message": "Internal Server Error"})

    payload = json.dumps({
        "repository": "valid/project",
        "caller_claims": {"owner": "valid", "name": "project"}
    })

    result_json = contract.verify_project(payload)
    result = json.loads(result_json)

    assert result["verification_state"] == "INSUFFICIENT_DATA"
    assert result["final_decision"] == "INSUFFICIENT_DATA"
    assert result["independent_evidence"]["status"] == 500


# 6. Test: malformed submission
def test_malformed_submission(contract):
    result_json = contract.verify_project("THIS IS NOT JSON {{{")
    result = json.loads(result_json)

    assert result["verification_state"] == "REJECTED"
    assert result["final_decision"] == "REJECT"
    assert "Malformed JSON" in result["stages"][-1]["detail"]


# 7. Test: insufficient evidence (missing target)
def test_insufficient_evidence_missing_target(contract):
    payload = json.dumps({
        "caller_claims": {"stars": 10}
    })

    result_json = contract.verify_project(payload)
    result = json.loads(result_json)

    assert result["verification_state"] == "REJECTED"
    assert result["final_decision"] == "REJECT"
    assert "owner/repo" in result["stages"][-1]["detail"]


# 8. Test: verification record persistence
def test_verification_record_persistence(contract):
    set_github_mock(200, {
        "owner": {"login": "persistorg"},
        "name": "persistrepo",
        "private": False,
        "default_branch": "main",
        "stargazers_count": 12,
        "forks_count": 3
    })
    MockEqPrinciple.prompt_return = '{"verdict": "APPROVE", "rationale": "Stored properly"}'

    payload = json.dumps({
        "repository": "persistorg/persistrepo",
        "caller_claims": {"owner": "persistorg", "name": "persistrepo"}
    })

    contract.verify_project(payload)

    assert contract.get_verification_count() == 1

    stored_v1 = json.loads(contract.get_verification("v_1"))
    stored_latest = json.loads(contract.get_latest_verification())

    assert stored_v1["verification_id"] == "v_1"
    assert stored_latest["verification_id"] == "v_1"
    assert stored_v1["target_repository"] == "persistorg/persistrepo"


# 9. Test: deterministic checks happen before LLM adjudication
def test_deterministic_checks_before_llm(contract):
    set_github_mock(200, {
        "owner": {"login": "legit"},
        "name": "legitrepo",
        "private": False,
        "default_branch": "main"
    })
    # Even if LLM would approve, deterministic branch mismatch must halt at MISMATCH / DISPUTE
    MockEqPrinciple.prompt_return = '{"verdict": "APPROVE", "rationale": "LLM erroneously approved"}'

    payload = json.dumps({
        "repository": "legit/legitrepo",
        "caller_claims": {
            "owner": "legit",
            "name": "legitrepo",
            "default_branch": "wrong-branch"
        }
    })

    result_json = contract.verify_project(payload)
    result = json.loads(result_json)

    # Must be MISMATCH / DISPUTE due to deterministic failure
    assert result["verification_state"] == "MISMATCH"
    assert result["final_decision"] == "DISPUTE"
    assert "wrong-branch" in str(result["comparison_result"]["mismatches"])


# 10. Test: unavailable data never becomes PASS
def test_unavailable_data_never_becomes_pass(contract):
    # Test network failure / 503 Service Unavailable
    set_github_mock(503, {"error": "Gateway Timeout"})

    payload = json.dumps({
        "repository": "any/repo",
        "caller_claims": {"owner": "any", "name": "repo"}
    })

    result_json = contract.verify_project(payload)
    result = json.loads(result_json)

    assert result["verification_state"] != "VERIFIED"
    assert result["final_decision"] != "APPROVE"
    assert result["verification_state"] == "INSUFFICIENT_DATA"
    assert result["final_decision"] == "INSUFFICIENT_DATA"


# 11. Test: no fabricated telemetry
def test_no_fabricated_telemetry(contract):
    set_github_mock(200, {
        "owner": {"login": "clean"},
        "name": "telemetry",
        "private": False,
        "default_branch": "main"
    })

    payload = json.dumps({
        "repository": "clean/telemetry",
        "caller_claims": {"owner": "clean", "name": "telemetry"}
    })

    result_json = contract.verify_project(payload)
    result = json.loads(result_json)

    telemetry = result["telemetry"]
    assert telemetry["validator_count"] is None
    assert telemetry["votes"] is None
    assert telemetry["confidence"] is None
    assert telemetry["consensus_percentage"] is None
    assert telemetry["latency_ms"] is None
