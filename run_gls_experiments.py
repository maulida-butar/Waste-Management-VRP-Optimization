"""
Project: Waste Management VRP Optimization - Universitas Gunadarma
File: run_gls_experiments.py
Author: Maulida Boru Butar Butar

Purpose:
    Repeats the Google OR-Tools Guided Local Search experiment for the
    Normal, Buffered, and Peak demand scenarios.

Outputs:
    1. Run-level results CSV
    2. Scenario summary CSV
    3. Route-frequency CSV
    4. Experiment metadata JSON

Important:
    Repeated GLS runs assess repeatability and empirical stability.
    They do not prove global optimality. Optimality must be established
    separately using an exact solver or exact dynamic-programming method.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def import_solver() -> tuple[Callable[..., dict[str, Any]], dict[str, Any]]:
    """
    Import solve_cvrp from the revised solver.

    The first import name matches the revised file supplied for this study.
    The fallback supports users who rename the file to VRP_Solver.py.
    """
    try:
        from VRP_Solver_revised import solve_cvrp, SCENARIOS
        return solve_cvrp, SCENARIOS
    except ImportError as revised_error:
        try:
            from VRP_Solver import solve_cvrp, SCENARIOS
            return solve_cvrp, SCENARIOS
        except ImportError as original_error:
            raise ImportError(
                "Could not import the revised solver. Place "
                "'run_gls_experiments.py' in the same folder as "
                "'VRP_Solver_revised.py', or rename the solver to "
                "'VRP_Solver.py' and ensure it contains solve_cvrp() "
                "and SCENARIOS."
            ) from original_error


solve_cvrp, SCENARIOS = import_solver()


def canonical_route_signature(result: dict[str, Any]) -> str:
    """
    Create a route signature for frequency analysis.

    Trip labels are treated as interchangeable. This is important for the
    Peak scenario because OR-Tools may swap virtual trip indices while
    producing the same operational solution.
    """
    route_texts = sorted(
        trip["route_text"]
        for trip in result.get("trips", [])
    )
    return " || ".join(route_texts)


def safe_mean(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def safe_median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def safe_pstdev(values: list[float]) -> float | None:
    return statistics.pstdev(values) if values else None


def safe_min(values: list[float]) -> float | None:
    return min(values) if values else None


def safe_max(values: list[float]) -> float | None:
    return max(values) if values else None


def round_or_none(value: float | None, digits: int = 6) -> float | None:
    return None if value is None else round(value, digits)


def run_scenario_experiments(
    scenario: str,
    runs: int,
    time_limit_seconds: int,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    """Run repeated GLS experiments for one scenario."""
    if runs <= 0:
        raise ValueError("runs must be greater than zero.")

    run_records: list[dict[str, Any]] = []
    route_counter: Counter[str] = Counter()

    for run_id in range(1, runs + 1):
        result = solve_cvrp(
            scenario=scenario,
            time_limit_seconds=time_limit_seconds,
        )

        raw_status = result.get("status", "UNKNOWN")
        solution_found = raw_status == "FEASIBLE"

        # Use a more precise label in the experiment output.
        experiment_status = (
            "HEURISTIC_SOLUTION_FOUND"
            if solution_found
            else raw_status
        )

        if solution_found:
            signature = canonical_route_signature(result)
            route_counter[signature] += 1

            total_distance = float(result["total_distance_km"])
            runtime = float(result["runtime_seconds"])

            improvement_percent = result.get("improvement_percent")
            if improvement_percent is not None:
                improvement_percent = float(improvement_percent)

            run_record = {
                "scenario": scenario,
                "run_id": run_id,
                "status": experiment_status,
                "total_distance_km": total_distance,
                "runtime_seconds": runtime,
                "used_trips": result["used_trips"],
                "total_demand_boxes": result["total_demand_boxes"],
                "route_signature": signature,
                "manual_route_distance_km": result[
                    "manual_route_distance_km"
                ],
                "manual_single_trip_feasible": result[
                    "manual_single_trip_feasible"
                ],
                "improvement_percent": improvement_percent,
            }
        else:
            run_record = {
                "scenario": scenario,
                "run_id": run_id,
                "status": experiment_status,
                "total_distance_km": None,
                "runtime_seconds": result.get("runtime_seconds"),
                "used_trips": None,
                "total_demand_boxes": None,
                "route_signature": "",
                "manual_route_distance_km": None,
                "manual_single_trip_feasible": None,
                "improvement_percent": None,
            }

        run_records.append(run_record)

        print(
            f"[{scenario.upper()}] "
            f"Run {run_id:02d}/{runs}: "
            f"{run_record['status']}"
            + (
                f", distance={run_record['total_distance_km']:.3f} km"
                f", runtime={run_record['runtime_seconds']:.4f} s"
                if solution_found
                else ""
            )
        )

    feasible_records = [
        record
        for record in run_records
        if record["status"] == "HEURISTIC_SOLUTION_FOUND"
    ]

    distances = [
        float(record["total_distance_km"])
        for record in feasible_records
    ]
    runtimes = [
        float(record["runtime_seconds"])
        for record in feasible_records
    ]

    if route_counter:
        best_route_signature, best_route_frequency = route_counter.most_common(1)[0]
    else:
        best_route_signature, best_route_frequency = "", 0

    improvement_values = [
        float(record["improvement_percent"])
        for record in feasible_records
        if record["improvement_percent"] is not None
    ]

    summary = {
        "scenario": scenario,
        "runs_requested": runs,
        "feasible_runs": len(feasible_records),
        "no_solution_runs": runs - len(feasible_records),
        "unique_route_solutions": len(route_counter),
        "best_distance_km": round_or_none(safe_min(distances)),
        "mean_distance_km": round_or_none(safe_mean(distances)),
        "median_distance_km": round_or_none(safe_median(distances)),
        "population_sd_distance_km": round_or_none(
            safe_pstdev(distances)
        ),
        "minimum_distance_km": round_or_none(safe_min(distances)),
        "maximum_distance_km": round_or_none(safe_max(distances)),
        "mean_runtime_seconds": round_or_none(safe_mean(runtimes)),
        "population_sd_runtime_seconds": round_or_none(
            safe_pstdev(runtimes)
        ),
        "minimum_runtime_seconds": round_or_none(safe_min(runtimes)),
        "maximum_runtime_seconds": round_or_none(safe_max(runtimes)),
        "most_frequent_route": best_route_signature,
        "most_frequent_route_count": best_route_frequency,
        "most_frequent_route_percentage": round_or_none(
            (best_route_frequency / len(feasible_records) * 100)
            if feasible_records
            else None
        ),
        "manual_comparison_available": bool(improvement_values),
        # Keep three decimal places for the manuscript when reported.
        "mean_improvement_percent": round_or_none(
            safe_mean(improvement_values),
            digits=3,
        ),
        "time_limit_seconds_per_run": time_limit_seconds,
        "interpretation": (
            "Repeated GLS runs assess empirical repeatability only. "
            "They do not establish global optimality."
        ),
    }

    route_frequency_records = []
    for rank, (signature, frequency) in enumerate(
        route_counter.most_common(),
        start=1,
    ):
        route_frequency_records.append(
            {
                "scenario": scenario,
                "rank": rank,
                "route_signature": signature,
                "frequency": frequency,
                "percentage_of_feasible_runs": round(
                    frequency / len(feasible_records) * 100,
                    3,
                ) if feasible_records else None,
            }
        )

    return run_records, summary, route_frequency_records


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str] | None = None,
) -> None:
    """Write dictionaries to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)

    if fieldnames is None:
        if not rows:
            raise ValueError("fieldnames are required when rows are empty.")
        fieldnames = list(rows[0].keys())

    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: dict[str, Any]) -> None:
    """Write JSON with UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def print_summary(summary: dict[str, Any]) -> None:
    """Print a concise scenario summary."""
    print("\n" + "=" * 78)
    print(f"GLS REPLICATION SUMMARY: {summary['scenario'].upper()}")
    print("=" * 78)
    print(f"Runs requested           : {summary['runs_requested']}")
    print(f"Feasible runs            : {summary['feasible_runs']}")
    print(f"No-solution runs         : {summary['no_solution_runs']}")
    print(f"Unique route solutions   : {summary['unique_route_solutions']}")
    print(f"Best distance            : {summary['best_distance_km']} km")
    print(f"Mean distance            : {summary['mean_distance_km']} km")
    print(f"Median distance          : {summary['median_distance_km']} km")
    print(
        f"Population SD distance   : "
        f"{summary['population_sd_distance_km']} km"
    )
    print(f"Minimum distance         : {summary['minimum_distance_km']} km")
    print(f"Maximum distance         : {summary['maximum_distance_km']} km")
    print(
        f"Mean runtime             : "
        f"{summary['mean_runtime_seconds']} seconds"
    )
    print(
        f"Most frequent route      : "
        f"{summary['most_frequent_route_count']}/"
        f"{summary['feasible_runs']} feasible runs"
    )

    if summary["manual_comparison_available"]:
        print(
            f"Mean distance reduction  : "
            f"{summary['mean_improvement_percent']:.3f}%"
        )
    else:
        print(
            "Mean distance reduction  : Not reported because the "
            "documented manual single-trip route is capacity-infeasible."
        )

    print(
        "Interpretation            : Repetition measures empirical "
        "stability, not global optimality."
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run repeated OR-Tools Guided Local Search experiments "
            "for the Gunadarma waste-collection CVRP."
        )
    )
    parser.add_argument(
        "--scenario",
        choices=["normal", "buffered", "peak", "all"],
        default="all",
        help="Scenario to test. Default: all.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=30,
        help="Number of repetitions per scenario. Default: 30.",
    )
    parser.add_argument(
        "--time-limit",
        type=int,
        default=10,
        help="GLS time limit per run in seconds. Default: 10.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/gls_experiments"),
        help="Directory for CSV and JSON outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    if args.runs <= 0:
        raise ValueError("--runs must be greater than zero.")

    if args.time_limit <= 0:
        raise ValueError("--time-limit must be greater than zero.")

    scenarios = (
        ["normal", "buffered", "peak"]
        if args.scenario == "all"
        else [args.scenario]
    )

    all_run_records: list[dict[str, Any]] = []
    all_summaries: list[dict[str, Any]] = []
    all_route_frequencies: list[dict[str, Any]] = []

    experiment_started = datetime.now(timezone.utc)

    for scenario in scenarios:
        run_records, summary, route_frequencies = run_scenario_experiments(
            scenario=scenario,
            runs=args.runs,
            time_limit_seconds=args.time_limit,
        )

        all_run_records.extend(run_records)
        all_summaries.append(summary)
        all_route_frequencies.extend(route_frequencies)

        print_summary(summary)

    experiment_finished = datetime.now(timezone.utc)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    write_csv(
        args.output_dir / "gls_run_level_results.csv",
        all_run_records,
    )
    write_csv(
        args.output_dir / "gls_scenario_summary.csv",
        all_summaries,
    )

    route_frequency_fields = [
        "scenario",
        "rank",
        "route_signature",
        "frequency",
        "percentage_of_feasible_runs",
    ]
    write_csv(
        args.output_dir / "gls_route_frequency.csv",
        all_route_frequencies,
        fieldnames=route_frequency_fields,
    )

    metadata = {
        "experiment_name": "Gunadarma CVRP GLS repeated-run analysis",
        "experiment_started_utc": experiment_started.isoformat(),
        "experiment_finished_utc": experiment_finished.isoformat(),
        "elapsed_wall_clock_seconds": (
            experiment_finished - experiment_started
        ).total_seconds(),
        "scenarios": scenarios,
        "runs_per_scenario": args.runs,
        "time_limit_seconds_per_run": args.time_limit,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "python_executable": sys.executable,
        "method": {
            "solver": "Google OR-Tools Routing Solver",
            "first_solution_strategy": "PATH_CHEAPEST_ARC",
            "local_search_metaheuristic": "GUIDED_LOCAL_SEARCH",
        },
        "scientific_interpretation": (
            "These experiments quantify repeatability and solution "
            "variability. They do not provide an optimality certificate. "
            "Optimality must be evaluated separately against an exact method."
        ),
    }
    write_json(
        args.output_dir / "gls_experiment_metadata.json",
        metadata,
    )

    print("\n" + "=" * 78)
    print("OUTPUT FILES")
    print("=" * 78)
    print(
        (args.output_dir / "gls_run_level_results.csv").resolve()
    )
    print(
        (args.output_dir / "gls_scenario_summary.csv").resolve()
    )
    print(
        (args.output_dir / "gls_route_frequency.csv").resolve()
    )
    print(
        (args.output_dir / "gls_experiment_metadata.json").resolve()
    )


if __name__ == "__main__":
    main()
