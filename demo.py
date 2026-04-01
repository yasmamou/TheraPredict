#!/usr/bin/env python3
"""
TheraPredict MVP Demo — run a complete simulation from the command line.

Usage:
    PYTHONPATH=src python3 demo.py
"""

import json
import sys
import time

sys.path.insert(0, "src")

from theranostics.orchestrator import SimulationOrchestrator
from theranostics.models.simulation import SimulationRequest


def banner(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def main():
    banner("TheraPredict MVP - Digital Theranostic Simulator")

    orch = SimulationOrchestrator()

    # --- List available assets ---
    print("Available targets:")
    for t in orch.get_available_targets():
        print(f"  {t['name']:10s} - {t['full_name']:40s} | tumors: {', '.join(t['tumor_types'])}")

    print("\nAvailable agents:")
    for a in orch.get_available_agents():
        isotope = a['isotope'] or 'none'
        print(f"  {a['key']:25s} | {a['name']:30s} | {a['type']:15s} | isotope: {isotope}")

    # --- Simulation 1: HER2 IgG ---
    banner("Simulation 1: Trastuzumab-89Zr (IgG, HER2+, breast cancer)")

    req1 = SimulationRequest(
        target_name="HER2",
        tumor_type="breast",
        agent_key="trastuzumab-89Zr",
        dose_mbq=37.0,
        dose_mg=50.0,
        patient_age=55,
        patient_sex="female",
        patient_weight_kg=68.0,
        patient_height_cm=165.0,
        patient_egfr=95.0,
        tumor_volume_ml=40.0,
        tumor_target_density=140.0,
        duration_hours=168,
        time_step_hours=1.0,
        n_monte_carlo=100,
    )

    t0 = time.time()
    r1 = orch.run_simulation(req1)
    dt = time.time() - t0

    print_result(r1, dt)

    # --- Simulation 2: PSMA-617 ---
    banner("Simulation 2: PSMA-617 (177Lu, prostate cancer)")

    req2 = SimulationRequest(
        target_name="PSMA",
        tumor_type="prostate",
        agent_key="PSMA-617",
        dose_mbq=7400.0,
        patient_age=68,
        patient_sex="male",
        patient_weight_kg=82.0,
        patient_height_cm=178.0,
        patient_egfr=75.0,
        tumor_volume_ml=25.0,
        tumor_target_density=160.0,
        duration_hours=168,
        time_step_hours=1.0,
        n_monte_carlo=100,
    )

    t0 = time.time()
    r2 = orch.run_simulation(req2)
    dt = time.time() - t0

    print_result(r2, dt)

    # --- Simulation 3: DOTATATE ---
    banner("Simulation 3: DOTATATE-68Ga (PET, neuroendocrine tumor)")

    req3 = SimulationRequest(
        target_name="SSTR2",
        tumor_type="neuroendocrine",
        agent_key="DOTATATE-68Ga",
        dose_mbq=200.0,
        patient_age=52,
        patient_sex="male",
        patient_weight_kg=75.0,
        tumor_volume_ml=15.0,
        tumor_target_density=150.0,
        duration_hours=4,
        time_step_hours=0.05,
        n_monte_carlo=100,
    )

    t0 = time.time()
    r3 = orch.run_simulation(req3)
    dt = time.time() - t0

    print_result(r3, dt)

    # --- Comparison ---
    banner("Strategy Comparison: HER2 - IgG vs Nanobody")

    comp_requests = [
        SimulationRequest(
            agent_key="trastuzumab-89Zr",
            tumor_type="breast",
            dose_mbq=37.0,
            tumor_volume_ml=40.0,
            duration_hours=168,
            time_step_hours=1.0,
            n_monte_carlo=50,
        ),
        SimulationRequest(
            agent_key="her2-nanobody-68Ga",
            tumor_type="breast",
            dose_mbq=150.0,
            tumor_volume_ml=40.0,
            duration_hours=6,
            time_step_hours=0.1,
            n_monte_carlo=50,
        ),
    ]

    report = orch.run_comparison(comp_requests)
    print(f"Target: {report.target_assessment.target_name} in {report.target_assessment.tumor_type}")
    print(f"Expression score: {report.target_assessment.expression_score}")
    print(f"Evidence level: {report.target_assessment.evidence_level}")
    print()
    print("Ranked strategies:")
    for s in report.ranked_strategies:
        print(f"  #{s.rank} {s.agent_name}")
        print(f"     Scores: efficacy={s.scores.efficacy_score:.3f}, "
              f"safety={s.scores.safety_score:.3f}, "
              f"practical={s.scores.practical_score:.3f}")
        print(f"     Combined: {s.scores.combined_score:.3f} | Confidence: {s.confidence}")
        for d in s.key_drivers:
            print(f"     + {d}")
        for r in s.risks:
            print(f"     ! {r}")
        print()

    print(f"Recommendation: {report.overall_recommendation}")

    banner("Demo Complete")
    print("To start the web UI:")
    print("  1. API:      PYTHONPATH=src python3 -m uvicorn theranostics.api.main:app --port 8000")
    print("  2. Frontend: cd frontend && npm run dev")
    print("  3. Open:     http://localhost:3000")
    print()
    print("API docs: http://localhost:8000/docs")


def print_result(r, dt):
    print(f"Simulation completed in {dt:.2f}s ({r.n_monte_carlo_samples} MC samples)")
    print(f"Agent: {r.request_summary.get('agent', '?')}")
    print(f"Patient: {r.request_summary.get('patient_weight_kg', '?')} kg")
    print()
    print(f"  Tumor uptake:       {r.tumor_uptake_percent_id_per_g.value:.2f} nM "
          f"[{r.tumor_uptake_percent_id_per_g.ci_low:.2f} - {r.tumor_uptake_percent_id_per_g.ci_high:.2f}]")
    print(f"  Tumor/Background:   {r.tumor_to_background_ratio.value:.1f} "
          f"[{r.tumor_to_background_ratio.ci_low:.1f} - {r.tumor_to_background_ratio.ci_high:.1f}]")
    print(f"  Optimal imaging:    {r.optimal_imaging_time_hours.value:.0f}h "
          f"[{r.optimal_imaging_time_hours.ci_low:.0f} - {r.optimal_imaging_time_hours.ci_high:.0f}]")
    print(f"  Plasma half-life:   {r.plasma_half_life_hours:.1f}h")
    print()

    print("  Biodistribution (top organs at optimal time):")
    sorted_biodist = sorted(r.biodistribution_at_optimal.items(), key=lambda x: -x[1])
    for organ, val in sorted_biodist[:8]:
        bar = "#" * int(min(val / max(sorted_biodist[0][1], 1e-12) * 30, 30))
        print(f"    {organ:15s} {val:.6f} {bar}")
    print()

    if r.dosimetry:
        print("  Dosimetry:")
        print(f"    Tumor dose:        {r.dosimetry.tumor_dose_gy_per_gbq:.4f} Gy/GBq")
        print(f"    Dose-limiting:     {r.dosimetry.dose_limiting_organ} ({r.dosimetry.dose_limiting_value:.4f} Gy/GBq)")
        if r.dosimetry.therapeutic_index:
            print(f"    Therapeutic index: {r.dosimetry.therapeutic_index}")
        if r.dosimetry.tumor_to_kidney_ratio:
            print(f"    Tumor/Kidney:      {r.dosimetry.tumor_to_kidney_ratio}")
        print()

    print(f"  Confidence: {r.confidence.level} ({r.confidence.data_support})")
    for f in r.confidence.factors:
        print(f"    - {f}")


if __name__ == "__main__":
    main()
