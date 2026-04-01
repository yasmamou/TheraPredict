"""FastAPI application for the Theranostic Simulation Platform."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from theranostics.api.routes.simulate import router as simulate_router
from theranostics.api.routes.agents import router as agents_router
from theranostics.api.routes.simulate_v1 import router as v1_router

app = FastAPI(
    title="TheraPredict API",
    description=(
        "AI-Driven Digital Theranostic Simulation Platform V1. "
        "Simulate biodistribution, predict tumor uptake, compute dosimetry, "
        "estimate biological effects, and compare theranostic strategies. "
        "Full audit trail and confidence scoring at every step."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(simulate_router, prefix="/api")
app.include_router(agents_router, prefix="/api")
app.include_router(v1_router, prefix="/api")


@app.get("/")
async def root() -> dict:
    return {
        "name": "TheraPredict API",
        "version": "1.0.0",
        "description": "AI-Driven Digital Theranostic Simulation Platform V1",
        "docs": "/docs",
        "endpoints": {
            "v1_simulate": "/api/v1/simulate",
            "v1_simulate_offline": "/api/v1/simulate/offline",
            "v1_compare": "/api/v1/compare",
            "v1_targets": "/api/v1/targets",
            "v1_isotopes": "/api/v1/isotopes",
            "v1_agent_classes": "/api/v1/agent-classes",
            "legacy_simulate": "/api/simulate/",
            "legacy_compare": "/api/simulate/compare",
            "legacy_agents": "/api/agents",
        },
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy"}
