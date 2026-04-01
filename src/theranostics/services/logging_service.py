"""Structured logging service for TheraPredict V1.

Every module logs its work as structured JSON lines.
Each log entry includes: request_id, module, event, timestamp, confidence.

Log levels: DEBUG, INFO, WARNING, ERROR, AUDIT
"""

from __future__ import annotations

import json
import hashlib
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Log entry model
# ---------------------------------------------------------------------------

class PipelineLogEntry(BaseModel):
    """Single structured log entry."""

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    request_id: str = ""
    module: str = ""
    event: str = ""
    level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, AUDIT
    data: dict[str, Any] = Field(default_factory=dict)
    confidence: Optional[float] = None
    duration_ms: Optional[float] = None
    source: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Pipeline logger: collects all logs for a single request
# ---------------------------------------------------------------------------

class PipelineLogger:
    """Collects structured logs for one pipeline execution.

    Usage::

        logger = PipelineLogger(request_id="abc-123")
        logger.info("input_normalizer", "normalized", data={...})
        logger.warning("parameter_builder", "default_used", ...)
        logs = logger.get_logs()        # list[dict]
        logger.flush_to_file(log_dir)   # write JSONL
    """

    def __init__(self, request_id: str = "") -> None:
        self.request_id = request_id
        self._entries: list[PipelineLogEntry] = []
        self._py_logger = logging.getLogger("therapredict.pipeline")

    # -- convenience methods --------------------------------------------------

    def debug(self, module: str, event: str, **kwargs: Any) -> None:
        self._log("DEBUG", module, event, **kwargs)

    def info(self, module: str, event: str, **kwargs: Any) -> None:
        self._log("INFO", module, event, **kwargs)

    def warning(self, module: str, event: str, **kwargs: Any) -> None:
        self._log("WARNING", module, event, **kwargs)

    def error(self, module: str, event: str, **kwargs: Any) -> None:
        self._log("ERROR", module, event, **kwargs)

    def audit(self, module: str, event: str, **kwargs: Any) -> None:
        self._log("AUDIT", module, event, **kwargs)

    # -- core -----------------------------------------------------------------

    def _log(self, level: str, module: str, event: str, **kwargs: Any) -> None:
        entry = PipelineLogEntry(
            request_id=self.request_id,
            module=module,
            event=event,
            level=level,
            data=kwargs.get("data", {}),
            confidence=kwargs.get("confidence"),
            duration_ms=kwargs.get("duration_ms"),
            source=kwargs.get("source"),
            warnings=kwargs.get("warnings", []),
            errors=kwargs.get("errors", []),
        )
        self._entries.append(entry)

        # Also forward to Python logger for console/file output
        msg = f"[{self.request_id}] {module}.{event}"
        getattr(self._py_logger, level.lower(), self._py_logger.info)(msg)

    # -- retrieval ------------------------------------------------------------

    def get_logs(self) -> list[dict[str, Any]]:
        """Return all log entries as dicts."""
        return [e.model_dump(exclude_none=True) for e in self._entries]

    def get_logs_for_module(self, module: str) -> list[dict[str, Any]]:
        return [
            e.model_dump(exclude_none=True)
            for e in self._entries
            if e.module == module
        ]

    def get_warnings(self) -> list[str]:
        warnings: list[str] = []
        for e in self._entries:
            warnings.extend(e.warnings)
        return warnings

    def get_errors(self) -> list[str]:
        errors: list[str] = []
        for e in self._entries:
            errors.extend(e.errors)
        return errors

    # -- persistence ----------------------------------------------------------

    def flush_to_file(self, log_dir: str | Path) -> Path:
        """Write all entries as JSONL to *log_dir*/<request_id>.jsonl."""
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        fname = f"{self.request_id}.jsonl" if self.request_id else "unknown.jsonl"
        path = log_dir / fname
        with open(path, "a") as f:
            for entry in self._entries:
                f.write(json.dumps(entry.model_dump(exclude_none=True)) + "\n")
        return path


# ---------------------------------------------------------------------------
# Module timer context manager
# ---------------------------------------------------------------------------

class ModuleTimer:
    """Context manager that logs module execution time.

    Usage::

        with ModuleTimer(logger, "pbpk_engine", "simulation"):
            ...  # work
    """

    def __init__(self, logger: PipelineLogger, module: str, event: str) -> None:
        self.logger = logger
        self.module = module
        self.event = event
        self._start: float = 0

    def __enter__(self) -> "ModuleTimer":
        self._start = time.perf_counter()
        self.logger.info(self.module, f"{self.event}_started")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        elapsed_ms = (time.perf_counter() - self._start) * 1000
        if exc_type is not None:
            self.logger.error(
                self.module,
                f"{self.event}_failed",
                duration_ms=round(elapsed_ms, 2),
                errors=[str(exc_val)],
            )
        else:
            self.logger.info(
                self.module,
                f"{self.event}_completed",
                duration_ms=round(elapsed_ms, 2),
            )


# ---------------------------------------------------------------------------
# Hashing helpers for audit trail
# ---------------------------------------------------------------------------

def hash_dict(d: dict) -> str:
    """Deterministic SHA-256 of a dict for audit trail."""
    raw = json.dumps(d, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Setup Python logging
# ---------------------------------------------------------------------------

def setup_logging(level: str = "INFO") -> None:
    """Configure root Python logging for TheraPredict."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
