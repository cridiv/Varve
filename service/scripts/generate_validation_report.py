#!/usr/bin/env python3
"""
Varve Ground Truth Validation Report Generator (C2)

Usage:
  python service/scripts/generate_validation_report.py

Runs run_ground_truth_check() and writes a structured, human-readable
markdown report to docs/validation.md.
"""

import sys
import os

# Path setup
script_dir = os.path.dirname(os.path.abspath(__file__))
service_dir = os.path.dirname(script_dir)

if service_dir not in sys.path:
    sys.path.append(service_dir)

from services.validation_service import generate_validation_report


def main():
    generate_validation_report()


if __name__ == "__main__":
    main()
