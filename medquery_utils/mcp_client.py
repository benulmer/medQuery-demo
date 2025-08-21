from __future__ import annotations

import requests
from typing import Any, Dict, List, Optional


class MCPClient:
    """Thin HTTP client for the local MCP server."""

    def __init__(self, base_url: str, headers: Optional[Dict[str, str]] = None) -> None:
        self.base_url = base_url.rstrip("/")
        # Default to event-stream if not provided; allow overrides via env
        default_headers: Dict[str, str] = {"Accept": "text/event-stream"}
        self.headers: Dict[str, str] = {**default_headers, **(headers or {})}

    def health(self) -> Dict[str, Any]:
        r = requests.get(f"{self.base_url}/health", timeout=10, headers=self.headers)
        r.raise_for_status()
        return r.json()

    def patient_search(
        self,
        min_age: Optional[int] = None,
        conditions: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        payload: Dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }
        if min_age is not None:
            payload["min_age"] = min_age
        if conditions:
            payload["conditions"] = conditions
        r = requests.post(
            f"{self.base_url}/tool/patient_search",
            json=payload,
            timeout=30,
            headers=self.headers,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("results", [])

    def patient_get(self, external_id: Optional[str] = None, name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        payload: Dict[str, Any] = {}
        if external_id:
            payload["id"] = external_id
        if name:
            payload["name"] = name
        r = requests.post(
            f"{self.base_url}/tool/patient_get",
            json=payload,
            timeout=15,
            headers=self.headers,
        )
        r.raise_for_status()
        return r.json().get("patient")

    def patient_aggregate(self, min_age: Optional[int] = None, conditions: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        payload: Dict[str, Any] = {}
        if min_age is not None:
            payload["min_age"] = min_age
        if conditions:
            payload["conditions"] = conditions
        r = requests.post(
            f"{self.base_url}/tool/patient_aggregate",
            json=payload,
            timeout=30,
            headers=self.headers,
        )
        r.raise_for_status()
        return r.json().get("aggregates", [])

