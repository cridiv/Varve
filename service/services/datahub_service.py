"""
Varve DataHub Service — Step 9 (Write-back to DataHub GMS & Aspect Verification)

Core business logic:
- writeback_finding_to_datahub(finding_id): emits InstitutionalMemory aspect metadata to DataHub GMS.
- confirm_datahub_annotation(dataset_urn): verifies annotation aspect directly on DataHub side.
"""

import sys
import os
import time
from typing import Dict, Any

service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if service_dir not in sys.path:
    sys.path.append(service_dir)

from config.config import DATAHUB_GMS_URL, DATAHUB_GMS_TOKEN
from db.connection import get_db_connection
from services.ledger_service import append_to_ledger

from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.ingestion.graph.client import DataHubGraph, DataHubGraphConfig
from datahub.metadata.schema_classes import (
    InstitutionalMemoryClass,
    InstitutionalMemoryMetadataClass,
    AuditStampClass,
)


def get_datahub_emitter() -> DatahubRestEmitter:
    """Creates a DataHub REST Emitter instance."""
    return DatahubRestEmitter(
        gms_server=DATAHUB_GMS_URL,
        token=DATAHUB_GMS_TOKEN,
    )


def get_datahub_graph() -> DataHubGraph:
    """Creates a DataHubGraph client instance."""
    config = DataHubGraphConfig(
        server=DATAHUB_GMS_URL,
        token=DATAHUB_GMS_TOKEN,
    )
    return DataHubGraph(config)


def writeback_finding_to_datahub(finding_id: str) -> Dict[str, Any]:
    """
    Step 9.1: Emits a DataHub MetadataChangeProposal carrying an InstitutionalMemory
    aspect documentation annotation onto the specified lineage node dataset URN.
    """
    finding_query = """
        SELECT 
            f.finding_id,
            f.model_id,
            f.severity,
            f.validated,
            f.narrative,
            f.recommended_action,
            e.node_urn,
            e.actor
        FROM findings f
        JOIN lineage_events e ON f.related_event_id = e.event_id
        WHERE f.finding_id = %s;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(finding_query, (finding_id,))
            finding = cur.fetchone()

    if not finding:
        raise ValueError(f"Finding '{finding_id}' not found in database.")

    finding = dict(finding)
    dataset_urn = finding["node_urn"]

    finding_link_url = f"http://localhost:5173/findings/{finding_id}"
    annotation_text = (
        f"⚠️ Varve Risk Finding [{finding['severity'].upper()}]: {finding['narrative']} "
        f"Recommended Action: {finding['recommended_action']}"
    )

    current_time_ms = int(time.time() * 1000)
    audit_stamp = AuditStampClass(
        time=current_time_ms,
        actor="urn:li:corpuser:varve-agent",
    )

    memory_element = InstitutionalMemoryMetadataClass(
        url=finding_link_url,
        description=annotation_text,
        createStamp=audit_stamp,
    )

    memory_aspect = InstitutionalMemoryClass(
        elements=[memory_element]
    )

    mcp = MetadataChangeProposalWrapper(
        entityType="dataset",
        entityUrn=dataset_urn,
        aspect=memory_aspect,
    )

    print(f"Emitting MetadataChangeProposal to DataHub for URN: {dataset_urn}...")
    emitter = get_datahub_emitter()
    emitter.emit(mcp)

    update_sql = """
        UPDATE findings
        SET 
            written_back_at = NOW(),
            datahub_annotation_urn = %s
        WHERE finding_id = %s;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(update_sql, (dataset_urn, finding_id))
        conn.commit()

    print(f"✅ Write-back successful! Updated written_back_at timestamp in database.")

    # B2.2 Ledger event: writeback
    append_to_ledger(
        event_type="writeback",
        finding_id=finding_id,
        payload={
            "model_id": finding["model_id"],
            "dataset_urn": dataset_urn,
            "annotation_text": annotation_text,
            "link_url": finding_link_url,
            "status": "written_back",
        }
    )

    return {
        "finding_id": finding_id,
        "dataset_urn": dataset_urn,
        "annotation_text": annotation_text,
        "link_url": finding_link_url,
        "status": "written_back",
    }


def confirm_datahub_annotation(dataset_urn: str) -> bool:
    """
    Step 9.2: Direct lookup on DataHub GMS to confirm InstitutionalMemory aspect.
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
            print(f"  - Description: {elem.description[:90]}...")
            print(f"  - Created By:  {elem.createStamp.actor}")
        return True
    else:
        print(f"❌ Verification failed: No InstitutionalMemory aspect found on DataHub for {dataset_urn}")
        return False
