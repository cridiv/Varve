"""
Shared PostgreSQL database connection management for Varve.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from config.config import POSTGRES_DSN


def get_db_connection():
    """Returns a new psycopg2 database connection with RealDictCursor."""
    return psycopg2.connect(POSTGRES_DSN, cursor_factory=RealDictCursor)
