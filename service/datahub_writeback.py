"""
Backward-compatibility adapter for datahub_writeback.py.
Re-exports core functions from services.datahub_service.
"""

import sys
import os

service_dir = os.path.dirname(os.path.abspath(__file__))
if service_dir not in sys.path:
    sys.path.append(service_dir)

from services.datahub_service import (
    get_datahub_emitter,
    get_datahub_graph,
    writeback_finding_to_datahub,
    confirm_datahub_annotation,
)

__all__ = [
    "get_datahub_emitter",
    "get_datahub_graph",
    "writeback_finding_to_datahub",
    "confirm_datahub_annotation",
]
