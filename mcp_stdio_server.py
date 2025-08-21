#!/usr/bin/env python3
"""
FastMCP stdio server for MedQuery tools.

Tools exposed:
- patient_search(min_age?, conditions?, limit?, offset?)
- patient_get(id?, name?)
- patient_aggregate(min_age?, conditions?)

Environment:
- DATABASE_URL (default sqlite:///./medquery.db)
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

# This requires: pip install fastmcp
from fastmcp import FastMCP

from medquery_utils.repository import PatientRepository, PatientFilter


# Global repository instance (initialized in main)
repo: PatientRepository | None = None


# Create FastMCP server (stdio) and declare tools
mcp = FastMCP("MedQuery-MCP", stateless_http=True)


@mcp.tool()
def patient_search(
    min_age: Optional[int] = None,
    conditions: Optional[List[str]] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Search patients by filters (returns a list of patient dicts)."""
    if repo is None:
        return []
    pf = PatientFilter(min_age=min_age, condition_names=conditions)
    return repo.search_patients(pf, limit=limit, offset=offset)


@mcp.tool()
def patient_get(id: Optional[str] = None, name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get a single patient by external ID or exact name."""
    if repo is None:
        return None
    # Reuse search and match locally
    candidates = repo.search_patients(PatientFilter(), limit=1000, offset=0)
    for p in candidates:
        if id and p.get("id") == id:
            return p
        if name and p.get("name") == name:
            return p
    return None


@mcp.tool()
def patient_aggregate(
    min_age: Optional[int] = None,
    conditions: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Aggregate patient counts by medication with optional filters."""
    if repo is None:
        return []
    pf = PatientFilter(min_age=min_age, condition_names=conditions)
    rows = repo.aggregate_by_medication(pf)
    return [{"medication": med, "count": cnt} for med, cnt in rows]


if __name__ == "__main__":
    db_url = os.getenv("DATABASE_URL", "sqlite:///./medquery.db")
    repo = PatientRepository(db_url)
    # Use current FastMCP run method
    mcp.run()

