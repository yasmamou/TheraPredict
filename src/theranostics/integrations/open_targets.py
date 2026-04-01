"""Open Targets Platform integration.

Fetches target-disease associations, evidence scores, and target data.
API docs: https://platform-docs.opentargets.org/
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

import httpx

from theranostics.services.logging_service import PipelineLogger

MODULE = "knowledge_layer.open_targets"

BASE_URL = "https://api.platform.opentargets.org/api/v4/graphql"

# Map our target names to Ensembl gene IDs
_TARGET_TO_ENSEMBL: dict[str, str] = {
    "PSMA": "ENSG00000086205",   # FOLH1
    "SSTR2": "ENSG00000180616",  # SSTR2
    "HER2": "ENSG00000141736",   # ERBB2
    "FAP": "ENSG00000078098",    # FAP
    "CD20": "ENSG00000156738",   # MS4A1
}

# Map our indication names to EFO disease IDs
_INDICATION_TO_EFO: dict[str, str] = {
    "prostate_cancer": "EFO_0001663",
    "breast_cancer": "EFO_0000305",
    "neuroendocrine_tumor": "EFO_0000621",
    "lymphoma": "EFO_0000574",
    "solid_tumor": "EFO_0000616",
    "colorectal_cancer": "EFO_0000365",
    "lung_cancer": "EFO_0001071",
    "gastric_cancer": "EFO_0000178",
    "pancreatic_cancer": "EFO_0002618",
    "thyroid_cancer": "EFO_0002892",
}

CACHE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "cache" / "open_targets"


class OpenTargetsClient:
    """Client for the Open Targets Platform GraphQL API."""

    def __init__(self, cache_dir: Path = CACHE_DIR, timeout: float = 15.0) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    def get_target_disease_association(
        self,
        target_name: str,
        indication: str,
        logger: PipelineLogger,
    ) -> Optional[dict[str, Any]]:
        """Fetch association score between target and disease."""
        ensembl_id = _TARGET_TO_ENSEMBL.get(target_name)
        efo_id = _INDICATION_TO_EFO.get(indication)

        if not ensembl_id or not efo_id:
            logger.warning(MODULE, "missing_id_mapping", data={
                "target": target_name, "indication": indication,
                "ensembl_id": ensembl_id, "efo_id": efo_id,
            })
            return None

        cache_key = f"assoc_{target_name}_{indication}"
        cached = self._read_cache(cache_key)
        if cached is not None:
            logger.info(MODULE, "cache_hit", data={"cache_key": cache_key})
            return cached

        query = """
        query associationScore($ensemblId: String!, $efoId: String!) {
            disease(efoId: $efoId) {
                id
                name
                associatedTargets(page: {index: 0, size: 50}) {
                    rows {
                        target {
                            id
                            approvedSymbol
                        }
                        score
                        datatypeScores {
                            id
                            score
                        }
                    }
                }
            }
        }
        """
        variables = {"ensemblId": ensembl_id, "efoId": efo_id}

        t0 = time.time()
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(BASE_URL, json={"query": query, "variables": variables})
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.error(MODULE, "api_call_failed", data={
                "endpoint": BASE_URL, "error": str(e),
            })
            return None

        elapsed_ms = (time.time() - t0) * 1000
        logger.info(MODULE, "api_call_success", data={
            "endpoint": "graphql/associatedTargets",
            "target": target_name,
            "indication": indication,
        }, duration_ms=round(elapsed_ms, 2))

        # Parse: find our target in the results
        disease_data = data.get("data", {}).get("disease")
        if not disease_data:
            logger.warning(MODULE, "no_disease_data", data={"efo_id": efo_id})
            return None

        rows = disease_data.get("associatedTargets", {}).get("rows", [])
        result = None
        for row in rows:
            if row.get("target", {}).get("id") == ensembl_id:
                result = {
                    "target": target_name,
                    "indication": indication,
                    "disease_name": disease_data.get("name", ""),
                    "overall_score": row.get("score", 0),
                    "datatype_scores": {
                        d["id"]: d["score"]
                        for d in row.get("datatypeScores", [])
                    },
                    "source": "open_targets",
                    "ensembl_id": ensembl_id,
                    "efo_id": efo_id,
                }
                break

        if result is None:
            logger.info(MODULE, "target_not_in_disease_associations", data={
                "target": target_name, "indication": indication,
            })
            result = {
                "target": target_name,
                "indication": indication,
                "overall_score": 0,
                "source": "open_targets",
                "note": "Target not found in disease associations",
            }

        self._write_cache(cache_key, result)
        return result

    def get_target_info(
        self,
        target_name: str,
        logger: PipelineLogger,
    ) -> Optional[dict[str, Any]]:
        """Fetch basic target information."""
        ensembl_id = _TARGET_TO_ENSEMBL.get(target_name)
        if not ensembl_id:
            return None

        cache_key = f"target_{target_name}"
        cached = self._read_cache(cache_key)
        if cached is not None:
            logger.info(MODULE, "cache_hit", data={"cache_key": cache_key})
            return cached

        query = """
        query targetInfo($ensemblId: String!) {
            target(ensemblId: $ensemblId) {
                id
                approvedSymbol
                approvedName
                biotype
                subcellularLocations {
                    location
                    source
                    termSL
                }
                tractability {
                    label
                    modality
                    value
                }
            }
        }
        """
        variables = {"ensemblId": ensembl_id}

        t0 = time.time()
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(BASE_URL, json={"query": query, "variables": variables})
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.error(MODULE, "api_call_failed", data={"error": str(e)})
            return None

        elapsed_ms = (time.time() - t0) * 1000
        target_data = data.get("data", {}).get("target")
        if not target_data:
            logger.warning(MODULE, "no_target_data", data={"ensembl_id": ensembl_id})
            return None

        result = {
            "target": target_name,
            "approved_symbol": target_data.get("approvedSymbol"),
            "approved_name": target_data.get("approvedName"),
            "biotype": target_data.get("biotype"),
            "subcellular_locations": [
                loc.get("location") for loc in target_data.get("subcellularLocations", [])
            ],
            "tractability": target_data.get("tractability", []),
            "source": "open_targets",
        }

        logger.info(MODULE, "target_info_retrieved", data={
            "target": target_name,
        }, duration_ms=round(elapsed_ms, 2))

        self._write_cache(cache_key, result)
        return result

    # -- Cache ----------------------------------------------------------------

    def _read_cache(self, key: str) -> Optional[dict]:
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def _write_cache(self, key: str, data: dict) -> None:
        path = self.cache_dir / f"{key}.json"
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass
