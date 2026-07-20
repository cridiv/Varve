"""
Varve DataHub Write-Back Service — Step 9

Writes risk findings back to DataHub GMS as metadata annotations (InstitutionalMemory / Documentation aspects)
on the dataset lineage node.
"""

import sys
import os
import time
from typing import Dict, Any, Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import psycopg2
from psycopg2.extras import RealDictCursor
from datahub.ingestion.graph.client import DataHubGraph, DatahubClientConfig
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.metadata.schema_classes import (
    InstitutionalMemoryClass,
    InstitutionalMemoryMetadataClass,
    AuditStampClass,
)

from config.config import DATAHUB_GMS_URL, DATAHUB_GMS_TOKEN, POSTGRES_DSN


def get_db_connection():
    return psycopg2.connect(POSTGRES_DSN, cursor_factory=RealDictCursor)


def get_datahub_graph() -> DataHubGraph:
    """Returns a DataHubGraph client connected to GMS."""
    config = DatahubClientConfig(server=DATAHUB_GMS_URL, token=DATAHUB_GMS_TOKEN)
    return DataHubGraph(config)


def writeback_finding_to_datahub(finding_id: str) -> Dict[str, Any]:
    """
    Step 9.1: Emits an InstitutionalMemory (Documentation) metadata annotation aspect
    to DataHub for the specified finding's model_id dataset node.
    """
    # Fetch finding details
    query = """
        SELECT f.finding_id, f.model_id, f.severity, f.validated, f.narrative, f.recommended_action, f.written_back_at, e.actor
        FROM findings f
        JOIN lineage_events e ON f.related_event_id = e.event_id
        WHERE f.finding_id = %s;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (finding_id,))
            finding = cur.fetchone()

    if not finding:
        raise ValueError(f"Finding '{finding_id}' not found.")

    finding = dict(finding)
    dataset_urn = finding["model_id"]

    annotation_text = (
        f"⚠️ Varve Risk Finding [{finding['severity'].upper()}]: "
        f"{finding['narrative']} "
        f"Recommended Action: {finding['recommended_action']}"
    )

    now_ms = int(time.time() * 1000)

    # Construct InstitutionalMemory aspect for DataHub
    memory_aspect = InstitutionalMemoryClass(
        elements=[
            InstitutionalMemoryMetadataClass(
                url=f"http://localhost:5173/findings/{finding_id}",
                description=annotation_text,
                createStamp=AuditStampClass(
                    time=now_ms,
                    actor="urn:li:corpuser:varve-agent",
                ),
            )
        ]
    )

    mcp = MetadataChangeProposalWrapper(
        entityType="dataset",
        entityUrn=dataset_urn,
        aspect=memory_aspect,
    )

    # Emit MCP to DataHub GMS
    graph = get_datahub_graph()
    print(f"Emitting MetadataChangeProposal to DataHub for URN: {dataset_urn}...")
    graph.emit_mcp(mcp)

    # Update written_back_at timestamp in Postgres
    update_query = """
        UPDATE findings 
        SET written_back_at = NOW(),
            datahub_annotation_urn = %s
        WHERE finding_id = %s
        RETURNING written_back_at;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(update_query, (f"{dataset_urn}/institutionalMemory", finding_id))
            updated_row = cur.fetchone()

    print(f"✅ Write-back successful! Updated written_back_at timestamp in database.")
    return {
        "finding_id": finding_id,
        "dataset_urn": dataset_urn,
        "annotation_text": annotation_text,
        "written_back_at": updated_row["written_back_at"].isoformat(),
    }


def confirm_datahub_annotation(dataset_urn: str) -> Optional[InstitutionalMemoryClass]:
    """
    Step 9.2: Direct lookup on DataHub GMS to verify the annotation aspect
    actually exists on the dataset node.
    """
    print(f"\n--- Checking DataHub directly for annotation aspect on URN ---")
    print(f"Dataset URN: {dataset_urn}")

    graph = get_datahub_graph()
    aspect = graph.get_aspect(
        entity_urn=dataset_urn,
        aspect_type=InstitutionalMemoryClass,
    )

    if aspect and aspect.elements:
        print(f"✅ CONFIRMED ON DATAHUB SIDE: Found {len(aspect.elements)} documentation annotation(s):")
        for elem in aspect.elements:
            print(f"  - Link:        {elem.url}")
            print(f"  - Description: {elem.description[:120]}...")
            print(f"  - Created By:  {elem.createStamp.actor}")
        return aspect
    else:
        print(f"❌ Annotation aspect not found or empty on DataHub side.")
        return None


if __name__ == "__main__":
    # Test write-back on the high-severity finding
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT finding_id, model_id FROM findings WHERE severity = 'high' LIMIT 1;")
            finding = cur.fetchone()

    if finding:
        fid = str(finding["finding_id"])
        urn = finding["model_id"]
        res = writeback_finding_to_datahub(fid)
        confirm_datahub_annotation(urn)
