"""
Backward-compatibility adapter for generator.py.
Re-exports core functions from services.generator_service.
"""

import sys
import os

service_dir = os.path.dirname(os.path.abspath(__file__))
if service_dir not in sys.path:
    sys.path.append(service_dir)

from services.generator_service import (
    generate_finding_narrative,
    populate_findings,
    verify_findings_table,
)

__all__ = [
    "generate_finding_narrative",
    "populate_findings",
    "verify_findings_table",
]

if __name__ == "__main__":
    populate_findings()
    verify_findings_table()
