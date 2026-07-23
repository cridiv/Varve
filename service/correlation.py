"""
Backward-compatibility adapter for correlation.py.
Re-exports core functions from services.correlation_service.
"""

import sys
import os

service_dir = os.path.dirname(os.path.abspath(__file__))
if service_dir not in sys.path:
    sys.path.append(service_dir)

from services.correlation_service import (
    get_db_connection,
    get_matching_incidents_for_event,
    get_actor_cross_model_incidents,
    get_all_actor_events,
    classify_pattern,
    populate_patterns,
    run_ground_truth_check,
)

__all__ = [
    "get_db_connection",
    "get_matching_incidents_for_event",
    "get_actor_cross_model_incidents",
    "get_all_actor_events",
    "classify_pattern",
    "populate_patterns",
    "run_ground_truth_check",
]

if __name__ == "__main__":
    run_ground_truth_check()
    print("\n--- Populating patterns table ---")
    populate_patterns()
