"""Human Protein Atlas integration.

Fetches tissue-level protein expression data.
API: https://www.proteinatlas.org/api
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

import httpx

from theranostics.services.logging_service import PipelineLogger

MODULE = "knowledge_layer.hpa"

BASE_URL = "https://www.proteinatlas.org"

# Map our target names to gene names used by HPA
_TARGET_TO_GENE: dict[str, str] = {
    "PSMA": "FOLH1",
    "SSTR2": "SSTR2",
    "HER2": "ERBB2",
    "FAP": "FAP",
    "CD20": "MS4A1",
}

# Map HPA tissue names to our compartment names
_TISSUE_TO_COMPARTMENT: dict[str, str] = {
    "kidney": "kidney",
    "liver": "liver",
    "lung": "lungs",
    "heart muscle": "heart",
    "skeletal muscle": "muscle",
    "cerebral cortex": "brain",
    "spleen": "spleen",
    "bone marrow": "bone_marrow",
    "skin": "skin",
    "small intestine": "gut",
    "colon": "gut",
    "rectum": "gut",
    "salivary gland": "salivary_glands",
    "stomach": "gut",
    "adrenal gland": "adrenals",
    "thyroid gland": "thyroid",
    "pancreas": "pancreas",
    "prostate": "prostate",
    "breast": "breast",
    "testis": "testis",
    "ovary": "ovary",
    "lymph node": "lymph_nodes",
}

# Quantitative mapping of HPA expression levels
_EXPRESSION_LEVEL_SCORE: dict[str, float] = {
    "Not detected": 0.0,
    "Low": 0.15,
    "Medium": 0.45,
    "High": 0.85,
}

CACHE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "cache" / "hpa"


class HumanProteinAtlasClient:
    """Client for the Human Protein Atlas API."""

    def __init__(self, cache_dir: Path = CACHE_DIR, timeout: float = 15.0) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    def get_tissue_expression(
        self,
        target_name: str,
        logger: PipelineLogger,
    ) -> Optional[dict[str, Any]]:
        """Get tissue-level protein expression for a target gene.

        Returns normalized expression scores per compartment.
        """
        gene = _TARGET_TO_GENE.get(target_name)
        if not gene:
            logger.warning(MODULE, "no_gene_mapping", data={"target": target_name})
            return None

        cache_key = f"tissue_{gene}"
        cached = self._read_cache(cache_key)
        if cached is not None:
            logger.info(MODULE, "cache_hit", data={"cache_key": cache_key})
            return cached

        url = f"{BASE_URL}/{gene}.json"
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
            "endpoint": f"/{gene}.json",
            "target": target_name,
        }, duration_ms=round(elapsed_ms, 2))

        # Parse tissue expression from the response
        # HPA JSON can be a list or a single object
        if isinstance(data, list):
            gene_data = data[0] if data else {}
        else:
            gene_data = data

        # Extract tissue expression from "Tissue expression" field
        tissue_expr_raw = gene_data.get("Tissue expression", [])
        rna_expr_raw = gene_data.get("RNA tissue expression", [])

        expression_by_compartment: dict[str, float] = {}
        raw_tissue_data: list[dict] = []

        # Process protein expression data
        if isinstance(tissue_expr_raw, list):
            for entry in tissue_expr_raw:
                tissue = entry.get("Tissue", "")
                level = entry.get("Level", "Not detected")
                compartment = _TISSUE_TO_COMPARTMENT.get(tissue.lower(), None)
                score = _EXPRESSION_LEVEL_SCORE.get(level, 0.0)

                raw_tissue_data.append({
                    "tissue": tissue,
                    "level": level,
                    "score": score,
                    "compartment": compartment,
                })

                if compartment:
                    # Take max if multiple tissues map to same compartment
                    expression_by_compartment[compartment] = max(
                        expression_by_compartment.get(compartment, 0.0),
                        score,
                    )

        result = {
            "target": target_name,
            "gene": gene,
            "expression_by_compartment": expression_by_compartment,
            "raw_tissue_count": len(raw_tissue_data),
            "source": "human_protein_atlas",
        }

        logger.info(MODULE, "tissue_expression_parsed", data={
            "target": target_name,
            "compartments_with_expression": len(expression_by_compartment),
            "tissues_processed": len(raw_tissue_data),
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
