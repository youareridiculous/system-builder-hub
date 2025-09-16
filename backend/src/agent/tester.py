"""
Agent tester - validates generated builds
"""
import logging
import requests
import os
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def test_build(base_url: str, project_id: str, preview_url: str, apis=None):
    """Test the generated build by checking endpoints"""
    apis = apis or []
    summary = {"project_id": project_id, "checks": []}
    
    # Test readiness
    try:
        r = requests.get(base_url + "/readiness", timeout=3)
        summary["checks"].append({
            "check": "readiness",
            "status": r.status_code,
            "ok": r.status_code == 200
        })
    except Exception as e:
        summary["checks"].append({
            "check": "readiness",
            "error": str(e),
            "ok": False
        })

    # Test preview URL
    if preview_url:
        try:
            r = requests.get(base_url + preview_url, timeout=3)
            summary["checks"].append({
                "check": "preview",
                "status": r.status_code,
                "ok": r.status_code == 200
            })
        except Exception as e:
            summary["checks"].append({
                "check": "preview",
                "error": str(e),
                "ok": False
            })

    # Test API endpoints
    for api in apis:
        try:
            route = api.get("route", "")
            r = requests.get(base_url + route, timeout=3)
            summary["checks"].append({
                "check": f"api:{route}",
                "status": getattr(r, 'status_code', None),
                "ok": getattr(r, 'ok', False)
            })
        except Exception as e:
            summary["checks"].append({
                "check": f"api:{api.get('route', '')}",
                "error": str(e),
                "ok": False
            })
    
    # Overall status
    summary["ok"] = all(c.get("ok") for c in summary["checks"] if "ok" in c)
    
    logger.info(f"Test summary for {project_id}: {summary['ok']} ({len(summary['checks'])} checks)")
    return summary
