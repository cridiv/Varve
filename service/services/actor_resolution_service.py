"""
Varve Actor Identity Resolution Service
Maps free-text lineage_events.actor names ("J. Alvarez", "K. Vance", "Ian Chen") 
to DataHub owner URNs & display names, storing the match in database.
"""

import sys
import os
import re
from typing import Dict, Any, List, Optional

service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if service_dir not in sys.path:
    sys.path.append(service_dir)

from db.connection import get_db_connection
from services.datahub_service import get_datahub_graph, parse_owner_name


def init_actor_mapping_table():
    """Ensure actor_owner_mappings table exists in database."""
    query = """
        CREATE TABLE IF NOT EXISTS actor_owner_mappings (
            lineage_actor        TEXT PRIMARY KEY,
            datahub_owner_urn    TEXT NOT NULL,
            datahub_display_name TEXT NOT NULL,
            match_type           TEXT NOT NULL,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
        conn.commit()


def normalize_name(name_str: str) -> str:
    """Helper to clean name strings for comparison."""
    if not name_str:
        return ""
    cleaned = re.sub(r'\(.*?\)', '', name_str)
    return cleaned.strip().lower()


def fetch_dynamic_datahub_owners() -> List[Dict[str, Any]]:
    """
    Dynamically fetches known DataHub owners from:
    1. PostgreSQL findings table (routed_to_team column).
    2. DataHub GMS corpuser graph queries (if GMS is reachable).
    3. Core seed registries.
    """
    owners_map = {}

    # Seed baseline registries
    baseline = [
        {"urn": "urn:li:corpuser:EMP006", "display": "Ian Chen (Director of Data Engineering)", "keywords": ["ian", "chen", "emp006", "i. chen"]},
        {"urn": "urn:li:corpuser:jonny1", "display": "jonny1 (Data Owner)", "keywords": ["jonny", "jonny1", "j. alvarez", "j_alvarez"]},
        {"urn": "urn:li:corpuser:patrick1", "display": "patrick1 (Data Owner)", "keywords": ["patrick", "patrick1", "p. chen", "r. chen"]},
        {"urn": "urn:li:corpuser:k_vance", "display": "K. Vance (Data Owner)", "keywords": ["k. vance", "vance", "k_vance"]},
        {"urn": "urn:li:corpuser:m_santos", "display": "M. Santos (Data Owner)", "keywords": ["m. santos", "santos", "m_santos"]},
    ]
    for b in baseline:
        owners_map[b["urn"]] = b

    # Dynamic DB Discovery from findings.routed_to_team
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT routed_to_team FROM findings WHERE routed_to_team IS NOT NULL AND routed_to_team != '';")
                for r in cur.fetchall():
                    team_str = r["routed_to_team"]
                    clean_name = team_str.split("(")[0].strip()
                    slug = re.sub(r'[^a-z0-9_]', '_', clean_name.lower())
                    urn = f"urn:li:corpuser:{slug}"
                    if urn not in owners_map:
                        owners_map[urn] = {
                            "urn": urn,
                            "display": team_str,
                            "keywords": [clean_name.lower(), slug],
                        }
    except Exception as e:
        print(f"[warning] DB routed_to_team dynamic owner lookup fallback: {e}")

    # Dynamic GMS Discovery (if DataHub instance is running)
    try:
        graph = get_datahub_graph()
        urns = graph.get_urns_by_filter(entity_types=["corpuser"], query="*")
        for user_urn in urns:
            user_id = parse_owner_name(user_urn)
            if user_urn not in owners_map:
                owners_map[user_urn] = {
                    "urn": user_urn,
                    "display": f"{user_id} (DataHub User)",
                    "keywords": [user_id.lower()],
                }
    except Exception as e:
        print(f"[warning] DataHub GMS corpuser lookup fallback: {e}")

    return list(owners_map.values())


def match_actor_to_datahub_owner(actor_name: str) -> Dict[str, str]:
    """
    Given a lineage_events.actor name (e.g. 'J. Alvarez', 'K. Vance', 'Ian Chen', or any unknown actor),
    resolves against dynamic DataHub corpusers & routed team names.
    
    If the actor is NOT in the known list:
    - Constructs a valid, standardized DataHub Corpuser URN (urn:li:corpuser:{slug}).
    - Labels match_type as 'constructed_corpuser_urn' so unknown/new actors are fully handled.
    """
    norm_actor = normalize_name(actor_name)
    if not norm_actor:
        return {
            "datahub_owner_urn": "urn:li:corpuser:unknown",
            "datahub_display_name": "Unknown Contributor",
            "match_type": "default_fallback",
        }

    # Fetch dynamic list combining seed registry, findings DB table, and DataHub GMS graph
    known_owners = fetch_dynamic_datahub_owners()

    # 1. Exact or keyword match
    for owner in known_owners:
        norm_display = normalize_name(owner["display"])
        if norm_actor == norm_display or (len(norm_actor) > 3 and norm_actor in norm_display):
            return {
                "datahub_owner_urn": owner["urn"],
                "datahub_display_name": owner["display"],
                "match_type": "exact_display_match",
            }
        for kw in owner.get("keywords", []):
            if kw and (kw == norm_actor or (len(kw) > 3 and kw in norm_actor)):
                return {
                    "datahub_owner_urn": owner["urn"],
                    "datahub_display_name": owner["display"],
                    "match_type": "alias_keyword_match",
                }

    # 2. First initial + last name matching (e.g. "J. Alvarez" -> "jonny1", "I. Chen" -> "Ian Chen")
    actor_parts = norm_actor.replace(".", " ").split()
    if len(actor_parts) >= 2:
        initial = actor_parts[0][0]
        last_name = actor_parts[-1]
        for owner in known_owners:
            norm_disp = normalize_name(owner["display"])
            if last_name in norm_disp and norm_disp.startswith(initial):
                return {
                    "datahub_owner_urn": owner["urn"],
                    "datahub_display_name": owner["display"],
                    "match_type": "fuzzy_initial_match",
                }

    # 3. Dynamic Handler for Actors NOT in the known list:
    # Generates a valid DataHub corpuser URN format (e.g. urn:li:corpuser:john_doe)
    slug = re.sub(r'[^a-z0-9_]', '_', norm_actor)
    return {
        "datahub_owner_urn": f"urn:li:corpuser:{slug}",
        "datahub_display_name": f"{actor_name} (Data Owner)",
        "match_type": "constructed_corpuser_urn",
    }


def resolve_and_store_actor(actor_name: str) -> Dict[str, Any]:
    """
    Executes identity resolution for a given actor name and stores/updates in database.
    """
    init_actor_mapping_table()

    res = match_actor_to_datahub_owner(actor_name)
    owner_urn = res["datahub_owner_urn"]
    display_name = res["datahub_display_name"]
    match_type = res["match_type"]

    query = """
        INSERT INTO actor_owner_mappings (lineage_actor, datahub_owner_urn, datahub_display_name, match_type, created_at)
        VALUES (%s, %s, %s, %s, NOW())
        ON CONFLICT (lineage_actor) DO UPDATE SET
            datahub_owner_urn = EXCLUDED.datahub_owner_urn,
            datahub_display_name = EXCLUDED.datahub_display_name,
            match_type = EXCLUDED.match_type,
            created_at = NOW()
        RETURNING lineage_actor, datahub_owner_urn, datahub_display_name, match_type;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (actor_name, owner_urn, display_name, match_type))
            row = dict(cur.fetchone())
        conn.commit()

    return row


def resolve_all_lineage_actors() -> List[Dict[str, Any]]:
    """
    Scans all lineage_events, resolves each unique actor against DataHub owners,
    and stores the mappings.
    """
    init_actor_mapping_table()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT actor FROM lineage_events WHERE actor IS NOT NULL AND actor != '';")
            actors = [r["actor"] for r in cur.fetchall()]

    all_names = set(actors) | {"Ian Chen", "jonny1", "patrick1", "J. Alvarez", "K. Vance", "M. Santos", "R. Chen"}

    mappings = []
    for name in all_names:
        m = resolve_and_store_actor(name)
        mappings.append(m)

    return mappings


def get_all_actor_mappings() -> List[Dict[str, Any]]:
    """Returns all stored actor-to-owner mappings from database."""
    init_actor_mapping_table()
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as cnt FROM actor_owner_mappings;")
            cnt = cur.fetchone()["cnt"]

    if cnt == 0:
        resolve_all_lineage_actors()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT lineage_actor, datahub_owner_urn, datahub_display_name, match_type, created_at FROM actor_owner_mappings ORDER BY lineage_actor;")
            rows = [dict(r) for r in cur.fetchall()]

    return rows
