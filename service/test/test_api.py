"""
Test script for Step 7.3: Verifies FastAPI REST endpoints using TestClient.
"""

import sys
import os
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_api():
    print(f"\n=======================================================")
    print(f"   TESTING FASTAPI REST ENDPOINTS (Step 7.3)")
    print(f"=======================================================\n")

    # 1. Test /health
    resp = client.get("/health")
    print(f"► GET /health -> Status {resp.status_code}")
    print(f"  Response: {resp.json()}\n")
    assert resp.status_code == 200

    # 2. Test GET /models/risk-ranking (Step 7.1)
    resp = client.get("/models/risk-ranking")
    print(f"► GET /models/risk-ranking -> Status {resp.status_code}")
    rankings = resp.json()
    print(f"  Returned {len(rankings)} ranked items:")
    for item in rankings:
        print(f"  - Model: {item['model_name']} | Severity: {item['severity'].upper()} | Validated: {item['validated']} | Summary: {item['summary'][:70]}...")
    print("")
    assert resp.status_code == 200
    assert len(rankings) >= 2
    assert rankings[0]["severity"] == "high"

    # 3. Test GET /findings/{finding_id} (Step 7.2)
    sample_finding_id = rankings[0]["finding_id"]
    resp = client.get(f"/findings/{sample_finding_id}")
    print(f"► GET /findings/{sample_finding_id} -> Status {resp.status_code}")
    detail = resp.json()
    print(f"  Model Name:       {detail['model_name']}")
    print(f"  Severity:         {detail['severity'].upper()}")
    print(f"  Narrative:        {detail['narrative']}")
    print(f"  Recommended Act:  {detail['recommended_action']}")
    print(f"  Related Event:    Actor={detail['event_details']['actor']}, Node={detail['event_details']['node_type']}")
    print(f"  Matched Incident: {detail['matched_incident']['description'] if detail['matched_incident'] else 'None'}")
    assert resp.status_code == 200
    assert detail["finding_id"] == sample_finding_id

    print("\n✅ STEP 7 COMPLETE: All REST endpoints return valid JSON!")

if __name__ == "__main__":
    test_api()
