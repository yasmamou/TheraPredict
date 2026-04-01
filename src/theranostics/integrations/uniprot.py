"""UniProt integration.

Fetches protein information: subcellular location, function, features.
API: https://rest.uniprot.org/
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

import httpx

from theranostics.services.logging_service import PipelineLogger

MODULE = "knowledge_layer.uniprot"

BASE_URL = "https://rest.uniprot.org/uniprotkb"

# Map our target names to UniProt accession IDs (human, reviewed)
_TARGET_TO_UNIPROT: dict[str, str] = {
    "PSMA": "Q04609",   # FOLH1_HUMAN
    "SSTR2": "P30874",  # SSR2_HUMAN
    "HER2": "P04626",   # ERBB2_HUMAN
    "FAP": "Q12884",    # SEPC_HUMAN
    "CD20": "P11836",   # CD20_HUMAN
}

CACHE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "cache" / "uniprot"


class UniProtClient:
    """Client for the UniProt REST API."""

    def __init__(self, cache_dir: Path = CACHE_DIR, timeout: float = 15.0) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    def get_protein_info(
        self,
        target_name: str,
        logger: PipelineLogger,
    ) -> Optional[dict[str, Any]]:
        """Fetch protein information for a target."""
        accession = _TARGET_TO_UNIPROT.get(target_name)
        if not accession:
            logger.warning(MODULE, "no_uniprot_mapping", data={"target": target_name})
            return None

        cache_key = f"protein_{accession}"
        cached = self._read_cache(cache_key)
        if cached is not None:
            logger.info(MODULE, "cache_hit", data={"cache_key": cache_key})
            return cached

        url = f"{BASE_URL}/{accession}.json"
        t0 = time.time()
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.error(MODULE, "api_call_failed", data={
                "url": url, "error": str(e),
            })
            return None

        elapsed_ms = (time.time() - t0) * 1000
        logger.info(MODULE, "api_call_success", data={
            "endpoint": f"/{accession}.json",
            "target": target_name,
        }, duration_ms=round(elapsed_ms, 2))

        # Parse relevant fields
        protein_name = ""
        names = data.get("proteinDescription", {}).get("recommendedName", {})
        if names:
            protein_name = names.get("fullName", {}).get("value", "")

        # Subcellular locations
        subcellular = []
        for comment in data.get("comments", []):
            if comment.get("commentType") == "SUBCELLULAR LOCATION":
                for loc in comment.get("subcellularLocations", []):
                    loc_name = loc.get("location", {}).get("value", "")
                    if loc_name:
                        subcellular.append(loc_name)

        # Function
        function_text = ""
        for comment in data.get("comments", []):
            if comment.get("commentType") == "FUNCTION":
                texts = comment.get("texts", [])
                if texts:
                    function_text = texts[0].get("value", "")

        # Molecular weight from sequence
        mw_da = data.get("sequence", {}).get("molWeight", 0)

        # Transmembrane regions (relevant for accessibility)
        has_transmembrane = False
        is_type_i = False
        for feature in data.get("features", []):
            if feature.get("type") == "Transmembrane":
                has_transmembrane = True
            if feature.get("type") == "Topological domain":
                desc = feature.get("description", "")
                if "Extracellular" in desc:
                    is_type_i = True

        result = {
            "target": target_name,
            "accession": accession,
            "protein_name": protein_name,
            "molecular_weight_da": mw_da,
            "subcellular_locations": subcellular,
            "function": function_text,
            "has_transmembrane": has_transmembrane,
            "has_extracellular_domain": is_type_i,
            "source": "uniprot",
        }

        logger.info(MODULE, "protein_info_parsed", data={
            "target": target_name,
            "protein_name": protein_name,
            "locations": subcellular,
        })

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
