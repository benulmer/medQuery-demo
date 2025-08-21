#!/usr/bin/env python3
"""
Minimal MCP-style server for MedQuery (HTTP JSON tools).

Endpoints:
  GET  /mcp/tools                        -> list available tools
  POST /mcp/tool/patient_search          -> search patients
  POST /mcp/tool/patient_get             -> get single patient by id or name
  POST /mcp/tool/patient_aggregate       -> aggregate counts by medication
  GET  /mcp/health                       -> server health and DB stats

Config:
  DATABASE_URL (default sqlite:///./medquery.db)
"""

import os
from typing import Any, Dict, List
from flask import Flask, request, jsonify

from medquery_utils.repository import PatientRepository, PatientFilter


app = Flask(__name__)
STATELESS_HTTP = os.getenv("STATELESS_HTTP", "true").lower() == "true"

repo: PatientRepository


@app.route("/mcp/health")
def health() -> Any:
    try:
        count = repo.count_patients()
    except Exception as e:
        return jsonify({"status": "degraded", "error": str(e), "stateless_http": STATELESS_HTTP}), 500
    return jsonify({"status": "ok", "db_records": count, "stateless_http": STATELESS_HTTP})


@app.route("/mcp/tools", methods=["GET"])
def tools_list() -> Any:
    tools = [
        {
            "name": "patient_search",
            "description": "Search patients by filters (min_age, conditions)",
            "input_schema": {"min_age": "int?", "conditions": "string[]?", "limit": "int?", "offset": "int?"},
        },
        {
            "name": "patient_get",
            "description": "Get a single patient by external id or name",
            "input_schema": {"id": "string?", "name": "string?"},
        },
        {
            "name": "patient_aggregate",
            "description": "Aggregate patient counts by medication with optional filters",
            "input_schema": {"min_age": "int?", "conditions": "string[]?"},
        },
    ]
    return jsonify({"tools": tools, "stateless_http": STATELESS_HTTP})


@app.route("/mcp/tool/patient_search", methods=["POST"])
def patient_search() -> Any:
    payload: Dict[str, Any] = request.get_json(force=True, silent=True) or {}
    pf = PatientFilter(
        min_age=payload.get("min_age"),
        condition_names=payload.get("conditions"),
    )
    limit = int(payload.get("limit") or 50)
    offset = int(payload.get("offset") or 0)
    results = repo.search_patients(pf, limit=limit, offset=offset)
    return jsonify({"ok": True, "results": results, "limit": limit, "offset": offset})


@app.route("/mcp/tool/patient_get", methods=["POST"])
def patient_get() -> Any:
    payload: Dict[str, Any] = request.get_json(force=True, silent=True) or {}
    pid = payload.get("id")
    name = payload.get("name")

    # Reuse search with tight filters
    pf = PatientFilter()
    candidates: List[Dict[str, Any]] = repo.search_patients(pf, limit=1000, offset=0)
    match = None
    for p in candidates:
        if pid and p.get("id") == pid:
            match = p
            break
        if name and p.get("name") == name:
            match = p
            break
    return jsonify({"ok": True, "patient": match})


@app.route("/mcp/tool/patient_aggregate", methods=["POST"])
def patient_aggregate() -> Any:
    payload: Dict[str, Any] = request.get_json(force=True, silent=True) or {}
    pf = PatientFilter(
        min_age=payload.get("min_age"),
        condition_names=payload.get("conditions"),
    )
    rows = repo.aggregate_by_medication(pf)
    aggregates = [{"medication": m, "count": c} for m, c in rows]
    return jsonify({"ok": True, "aggregates": aggregates})


if __name__ == "__main__":
    db_url = os.getenv("DATABASE_URL", "sqlite:///./medquery.db")
    repo = PatientRepository(db_url)
    print(f"🧩 MCP server starting on http://0.0.0.0:8000 (stateless_http={STATELESS_HTTP})")
    app.run(host="0.0.0.0", port=8000, debug=True)

