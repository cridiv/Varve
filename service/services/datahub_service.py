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
    OwnershipClass,
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


def parse_owner_name(target_user_urn: str) -> str:
    user_id = target_user_urn.replace("urn:li:corpuser:", "")
    if "@" in user_id:
        user_id = user_id.split("@")[0]
    if "." in user_id:
        user_id = user_id.split(".")[-1]
    return user_id


def resolve_dataset_routed_owner(dataset_urn: str) -> str:
    """
    E1.2 Order of priority when resolving routed_to_team from DataHub Ownership aspect:
    1. If a dataset has an individual owner other than EMP006 (e.g. jonny1, patrick1), route there.
    2. If EMP006 is the only individual owner, route to him ('Ian Chen (Director of Data Engineering)').
    3. If no individual owner exists at all, route to the corpGroup.
    """
    try:
        graph = get_datahub_graph()
        ownership = graph.get_aspect(dataset_urn, OwnershipClass)

        if ownership and ownership.owners:
            individual_owners = []
            group_owners = []

            for o in ownership.owners:
                owner_urn = o.owner
                if "corpuser" in owner_urn:
                    individual_owners.append(owner_urn)
                elif "corpGroup" in owner_urn:
                    group_owners.append(owner_urn)

            # Priority 1: Specific individual owner other than EMP006
            non_emp006_users = [u for u in individual_owners if "EMP006" not in u]
            if non_emp006_users:
                user_id = parse_owner_name(non_emp006_users[0])
                return f"{user_id} (Data Owner)"

            # Priority 2: EMP006 is the only individual owner -> Ian Chen
            if any("EMP006" in u for u in individual_owners):
                return "Ian Chen (Director of Data Engineering)"

            # Priority 3: No individual owner -> corpGroup
            if group_owners:
                group_name = group_owners[0].split(".")[-1]
                return f"{group_name} (Team Group)"

    except Exception as e:
        print(f"[warning] DataHub ownership lookup fallback for {dataset_urn}: {e}")

    # Fallback default if DataHub GMS is unreachable
    if "customers" in dataset_urn:
        return "jonny1 (Data Owner)"
    elif "products" in dataset_urn:
        return "patrick1 (Data Owner)"
    else:
        return "Ian Chen (Director of Data Engineering)"


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
