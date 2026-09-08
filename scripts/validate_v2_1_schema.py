import requests
import json
import os
import sys

def validate_schema():
    contract_path = os.path.join(os.path.dirname(__file__), "..", "contracts", "TrustLensVerifierV2_1.py")
    with open(contract_path, "r", encoding="utf-8") as f:
        code = f.read()

    rpc_url = "https://studio.genlayer.com/api"
    payload = {
        "jsonrpc": "2.0",
        "method": "gen_getContractSchemaForCode",
        "params": [code],
        "id": 1
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    print("Submitting TrustLensVerifierV2_1.py to GenLayer Studio RPC for schema validation...")
    try:
        res = requests.post(rpc_url, json=payload, headers=headers, timeout=30)
        print("HTTP Status:", res.status_code)
        resp_json = res.json()
        print("Response:", json.dumps(resp_json, indent=2))
        
        if "result" in resp_json:
            result = resp_json["result"]
            print("\n[SUCCESS] Contract Schema Successfully Validated by GenLayer Studio!")
            print("Constructor:", result.get("ctor"))
            print("Methods:", list(result.get("methods", {}).keys()))
            return True
        else:
            print("\n[ERROR] Schema validation failed:", resp_json.get("error"))
            return False
    except Exception as e:
        print("\n[EXCEPTION] Failed to validate schema:", e)
        return False

if __name__ == "__main__":
    success = validate_schema()
    sys.exit(0 if success else 1)
