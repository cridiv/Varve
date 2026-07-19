"""
Step 1.2 milestone script.

What this does, in order:
1. Connects to your local DataHub instance
2. Searches for datasets (to sanity-check how much data is actually loaded)
3. Fetches one specific entity by URN and prints its metadata

Run with:
    DATAHUB_GMS_URL="http://localhost:8080" python3 test_datahub.py

No token needed for local quickstart's default open GMS endpoint,
but if you generated a personal access token, set DATAHUB_GMS_TOKEN too.
"""

import os
from datahub.ingestion.graph.client import DataHubGraph, DatahubClientConfig

GMS_URL = os.environ.get("DATAHUB_GMS_URL", "http://localhost:8080")
GMS_TOKEN = os.environ.get("DATAHUB_GMS_TOKEN")  # optional for local quickstart

print(f"Connecting to DataHub at {GMS_URL} ...")

config = DatahubClientConfig(server=GMS_URL, token=GMS_TOKEN)
graph = DataHubGraph(config)

# --- Step 1: sanity check how much data is actually loaded ---
print("\n--- Searching for datasets ---")
results = list(
    graph.get_urns_by_filter(
        entity_types=["dataset"],
        query="*",
    )
)
print(f"Total datasets found: {len(results)}")

if not results:
    print("No datasets found at all — the datapack load likely did not complete. Re-run:")
    print("  datahub datapack load showcase-ecommerce")
else:
    print("First 5 dataset URNs:")
    for urn in results[:5]:
        print(f"  {urn}")

# --- Step 2: fetch full metadata for one entity ---
if results:
    sample_urn = results[0]
    print(f"\n--- Fetching full metadata for one entity ---")
    print(f"URN: {sample_urn}")

    entity = graph.get_entity_semityped(sample_urn)
    print("\nMetadata aspects returned:")
    for aspect_name, aspect_value in entity.items():
        print(f"  {aspect_name}: {aspect_value}")

    # --- Step 3: check lineage on this same node ---
    print(f"\n--- Checking lineage for this entity ---")
    try:
        from datahub.metadata.schema_classes import UpstreamLineageClass

        upstream_aspect = graph.get_aspect(
            entity_urn=sample_urn,
            aspect_type=UpstreamLineageClass,
        )
        if upstream_aspect and upstream_aspect.upstreams:
            print(f"Found {len(upstream_aspect.upstreams)} upstream dependencies:")
            for up in upstream_aspect.upstreams:
                print(f"  {up.dataset}  (type: {up.type})")
        else:
            print("No upstreamLineage aspect found on this node (it may only have downstream consumers, or none).")
    except Exception as e:
        print(f"Lineage fetch failed: {e}")

print("\nDone. If you saw datasets, metadata, and no connection errors above, step 1.2 is complete.")