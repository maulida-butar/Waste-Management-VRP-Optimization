"""
Project: Waste Management VRP Optimization - Universitas Gunadarma
File: exact_validation.py
Author: Maulida Boru Butar Butar

Purpose:
    Computes the exact optimum for the 13-node directed waste-collection
    routing instances and compares it with the best GLS result.

Exact method:
    1. Held-Karp dynamic programming enumerates all customer subsets and
       all possible final nodes to obtain the minimum directed depot tour
       for every subset.
    2. For the Peak scenario, every capacity-feasible partition of the
       12 customers into two non-empty trips is evaluated exactly.

This procedure is computationally tractable because the case contains
only 12 collection nodes plus one depot.

Important:
    The exact objective uses the same integer-metre arc costs as the
    OR-Tools model:
        round(distance_km * 1000)
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def import_study_data() -> tuple[
    list[str],
    list[list[float]],
    dict[str, dict[str, Any]],
    int,
    int,
]:
    """
    Import the fixed study data from the revised solver.

    Keep this file in the same folder as VRP_Solver_revised.py.
    A fallback is provided when the revised solver is renamed
    to VRP_Solver.py.
    """
    try:
        from VRP_Solver_revised import (
            NODE_NAMES,
            DISTANCE_MATRIX_KM,
            SCENARIOS,
            VEHICLE_CAPACITY,
            DEPOT_INDEX,
        )
    except ImportError:
        try:
            from VRP_Solver import (
                NODE_NAMES,
                DISTANCE_MATRIX_KM,
                SCENARIOS,
                VEHICLE_CAPACITY,
                DEPOT_INDEX,
            )
        except ImportError as exc:
            raise ImportError(
                "Place exact_validation.py in the same folder as "
                "VRP_Solver_revised.py, or rename the revised solver "
                "to VRP_Solver.py."
            ) from exc

    return (
        NODE_NAMES,
        DISTANCE_MATRIX_KM,
        SCENARIOS,
        VEHICLE_CAPACITY,
        DEPOT_INDEX,
    )


(
    NODE_NAMES,
    DISTANCE_MATRIX_KM,
    SCENARIOS,
    VEHICLE_CAPACITY,
    DEPOT_INDEX,
) = import_study_data()


def validate_study_data() -> None:
    """Validate matrix, depot, node, and demand dimensions."""
    node_count = len(NODE_NAMES)

    if DEPOT_INDEX != 0:
        raise ValueError(
            "This exact implementation expects the depot at index 0."
        )

    if len(DISTANCE_MATRIX_KM) != node_count:
        raise ValueError(
            "Distance matrix row count does not match node count."
        )

    if any(len(row) != node_count for row in DISTANCE_MATRIX_KM):
        raise ValueError("Distance matrix must be square.")

    for scenario, values in SCENARIOS.items():
        if len(values["demands"]) != node_count:
            raise ValueError(
                f"Demand vector for '{scenario}' does not match "
                "the number of nodes."
            )

        if values["num_trips"] not in (1, 2):
            raise ValueError(
                "This exact validation currently supports one or "
                "two trips only."
            )


def build_integer_distance_matrix() -> list[list[int]]:
    """
    Convert directed distances from kilometres to integer metres.

    This must match the OR-Tools distance callback exactly.
    """
    return [
        [round(distance_km * 1000) for distance_km in row]
        for row in DISTANCE_MATRIX_KM
    ]


def compute_subset_loads(
    customer_demands: list[int],
) -> list[int]:
    """Compute total demand for every customer subset."""
    subset_count = 1 << len(customer_demands)
    loads = [0] * subset_count

    for mask in range(1, subset_count):
        least_significant_bit = mask & -mask
        customer_position = least_significant_bit.bit_length() - 1
        previous_mask = mask ^ least_significant_bit

        loads[mask] = (
            loads[previous_mask]
            + customer_demands[customer_position]
        )

    return loads


def held_karp_all_subsets(
    distance_m: list[list[int]],
) -> tuple[
    list[int],
    list[int],
    list[list[int]],
]:
    """
    Compute the exact minimum depot tour for every customer subset.

    Customers correspond to matrix indices 1..n. Bit position j
    represents customer matrix index j+1.

    Returns:
        tour_cost_m:
            Minimum closed-tour cost for each subset.
        tour_end_customer:
            Final customer position before returning to the depot.
        parent:
            Predecessor table used for route reconstruction.
    """
    customer_count = len(distance_m) - 1
    subset_count = 1 << customer_count
    infinity = 10**30

    # dp[mask][j] = exact minimum cost from depot, visiting exactly
    # the customers in mask, and ending at customer position j.
    dp = [
        [infinity] * customer_count
        for _ in range(subset_count)
    ]
    parent = [
        [-1] * customer_count
        for _ in range(subset_count)
    ]

    for customer_position in range(customer_count):
        mask = 1 << customer_position
        matrix_node = customer_position + 1
        dp[mask][customer_position] = distance_m[0][matrix_node]

    for mask in range(1, subset_count):
        remaining_end_nodes = mask

        while remaining_end_nodes:
            end_bit = (
                remaining_end_nodes
                & -remaining_end_nodes
            )
            end_position = end_bit.bit_length() - 1
            previous_mask = mask ^ end_bit

            if previous_mask:
                best_cost = infinity
                best_previous_position = -1
                remaining_previous_nodes = previous_mask

                while remaining_previous_nodes:
                    previous_bit = (
                        remaining_previous_nodes
                        & -remaining_previous_nodes
                    )
                    previous_position = (
                        previous_bit.bit_length() - 1
                    )

                    candidate_cost = (
                        dp[previous_mask][previous_position]
                        + distance_m[
                            previous_position + 1
                        ][end_position + 1]
                    )

                    if candidate_cost < best_cost:
                        best_cost = candidate_cost
                        best_previous_position = previous_position

                    remaining_previous_nodes ^= previous_bit

                dp[mask][end_position] = best_cost
                parent[mask][end_position] = (
                    best_previous_position
                )

            remaining_end_nodes ^= end_bit

    tour_cost_m = [infinity] * subset_count
    tour_end_customer = [-1] * subset_count
    tour_cost_m[0] = 0

    for mask in range(1, subset_count):
        remaining_end_nodes = mask

        while remaining_end_nodes:
            end_bit = (
                remaining_end_nodes
                & -remaining_end_nodes
            )
            end_position = end_bit.bit_length() - 1

            candidate_cost = (
                dp[mask][end_position]
                + distance_m[end_position + 1][0]
            )

            if candidate_cost < tour_cost_m[mask]:
                tour_cost_m[mask] = candidate_cost
                tour_end_customer[mask] = end_position

            remaining_end_nodes ^= end_bit

    return tour_cost_m, tour_end_customer, parent


def reconstruct_subset_route(
    subset_mask: int,
    tour_end_customer: list[int],
    parent: list[list[int]],
) -> list[int]:
    """Reconstruct one exact optimal depot tour for a subset."""
    if subset_mask == 0:
        return [0, 0]

    current_mask = subset_mask
    current_position = tour_end_customer[current_mask]
    reversed_customer_nodes: list[int] = []

    while current_position != -1:
        reversed_customer_nodes.append(current_position + 1)

        current_bit = 1 << current_position
        previous_position = parent[
            current_mask
        ][current_position]

        current_mask ^= current_bit
        current_position = previous_position

    customer_nodes = list(
        reversed(reversed_customer_nodes)
    )
    return [0] + customer_nodes + [0]


def calculate_route_cost_m(
    route: list[int],
    distance_m: list[list[int]],
) -> int:
    """Audit an exact reconstructed route."""
    return sum(
        distance_m[route[index]][route[index + 1]]
        for index in range(len(route) - 1)
    )


def solve_exact_scenario(
    scenario: str,
    distance_m: list[list[int]],
    tour_cost_m: list[int],
    tour_end_customer: list[int],
    parent: list[list[int]],
) -> dict[str, Any]:
    """Solve one scenario exactly."""
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}")

    scenario_data = SCENARIOS[scenario]
    demands = scenario_data["demands"]
    customer_demands = demands[1:]
    num_trips = scenario_data["num_trips"]

    customer_count = len(customer_demands)
    full_mask = (1 << customer_count) - 1
    subset_loads = compute_subset_loads(customer_demands)

    if num_trips == 1:
        if subset_loads[full_mask] > VEHICLE_CAPACITY:
            raise ValueError(
                f"Scenario '{scenario}' is infeasible for one trip."
            )

        selected_masks = [full_mask]
        exact_cost_m = tour_cost_m[full_mask]

    elif num_trips == 2:
        infinity = 10**30
        exact_cost_m = infinity
        best_first_mask: int | None = None

        # Enumerate every non-empty two-way partition.
        # The mask <= complement condition removes duplicate
        # trip-label permutations without removing any solution.
        for first_mask in range(1, full_mask):
            second_mask = full_mask ^ first_mask

            if first_mask > second_mask:
                continue

            if (
                subset_loads[first_mask] > VEHICLE_CAPACITY
                or subset_loads[second_mask] > VEHICLE_CAPACITY
            ):
                continue

            candidate_cost_m = (
                tour_cost_m[first_mask]
                + tour_cost_m[second_mask]
            )

            if candidate_cost_m < exact_cost_m:
                exact_cost_m = candidate_cost_m
                best_first_mask = first_mask

        if best_first_mask is None:
            raise RuntimeError(
                f"No capacity-feasible exact partition found "
                f"for scenario '{scenario}'."
            )

        selected_masks = [
            best_first_mask,
            full_mask ^ best_first_mask,
        ]

    else:
        raise ValueError(
            "Only one-trip and two-trip exact validation "
            "are supported."
        )

    trips: list[dict[str, Any]] = []
    audit_total_m = 0

    for trip_id, subset_mask in enumerate(
        selected_masks,
        start=1,
    ):
        route_indices = reconstruct_subset_route(
            subset_mask,
            tour_end_customer,
            parent,
        )
        audited_cost_m = calculate_route_cost_m(
            route_indices,
            distance_m,
        )

        if audited_cost_m != tour_cost_m[subset_mask]:
            raise RuntimeError(
                "Route reconstruction audit failed."
            )

        audit_total_m += audited_cost_m
        load_boxes = subset_loads[subset_mask]

        trips.append(
            {
                "trip_id": trip_id,
                "subset_mask": subset_mask,
                "route_indices": route_indices,
                "route_names": [
                    NODE_NAMES[node]
                    for node in route_indices
                ],
                "route_text": " -> ".join(
                    NODE_NAMES[node]
                    for node in route_indices
                ),
                "distance_m": audited_cost_m,
                "distance_km": audited_cost_m / 1000,
                "load_boxes": load_boxes,
                "capacity_boxes": VEHICLE_CAPACITY,
                "utilization_percent": (
                    load_boxes / VEHICLE_CAPACITY
                ) * 100,
            }
        )

    if audit_total_m != exact_cost_m:
        raise RuntimeError(
            "Exact total-distance audit failed."
        )

    return {
        "scenario": scenario,
        "exact_status": "EXACT_OPTIMUM",
        "exact_method": (
            "Held-Karp dynamic programming with exhaustive "
            "capacity-feasible subset partitioning"
        ),
        "number_of_customers": customer_count,
        "configured_trips": num_trips,
        "total_demand_boxes": sum(customer_demands),
        "exact_distance_m": exact_cost_m,
        "exact_distance_km": exact_cost_m / 1000,
        "trips": trips,
    }


def read_gls_summary(
    summary_path: Path,
) -> dict[str, float]:
    """Read best GLS distances from the repeated-run summary CSV."""
    if not summary_path.exists():
        return {}

    best_by_scenario: dict[str, float] = {}

    with summary_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            scenario = row["scenario"].strip().lower()
            value = row.get("best_distance_km", "").strip()

            if value:
                best_by_scenario[scenario] = float(value)

    return best_by_scenario


def add_gls_comparison(
    exact_result: dict[str, Any],
    gls_best_by_scenario: dict[str, float],
) -> dict[str, Any]:
    """Add the GLS best distance and optimality gap."""
    scenario = exact_result["scenario"]
    gls_best_km = gls_best_by_scenario.get(scenario)

    if gls_best_km is None:
        exact_result["gls_best_distance_km"] = None
        exact_result["optimality_gap_percent"] = None
        exact_result["gls_matches_exact_optimum"] = None
        return exact_result

    exact_distance_m = exact_result["exact_distance_m"]
    gls_best_m = round(gls_best_km * 1000)

    gap_percent = (
        (gls_best_m - exact_distance_m)
        / exact_distance_m
    ) * 100

    exact_result["gls_best_distance_km"] = (
        gls_best_m / 1000
    )
    exact_result["optimality_gap_percent"] = round(
        gap_percent,
        6,
    )
    exact_result["gls_matches_exact_optimum"] = (
        gls_best_m == exact_distance_m
    )

    return exact_result


def write_summary_csv(
    output_path: Path,
    results: list[dict[str, Any]],
) -> None:
    """Write scenario-level exact-validation results."""
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "scenario",
        "exact_status",
        "exact_method",
        "number_of_customers",
        "configured_trips",
        "total_demand_boxes",
        "exact_distance_m",
        "exact_distance_km",
        "gls_best_distance_km",
        "optimality_gap_percent",
        "gls_matches_exact_optimum",
    ]

    with output_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(results)


def write_json(
    output_path: Path,
    results: list[dict[str, Any]],
) -> None:
    """Write full exact routes and validation details."""
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_path.write_text(
        json.dumps(
            results,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def print_exact_result(
    result: dict[str, Any],
) -> None:
    """Print one exact-validation result."""
    print("=" * 78)
    print(
        f"EXACT VALIDATION: "
        f"{result['scenario'].upper()}"
    )
    print("=" * 78)
    print(f"Status          : {result['exact_status']}")
    print(f"Method          : {result['exact_method']}")
    print(
        f"Exact distance  : "
        f"{result['exact_distance_km']:.3f} km"
    )

    for trip in result["trips"]:
        print("-" * 78)
        print(
            f"Trip {trip['trip_id']}: "
            f"{trip['route_text']}"
        )
        print(
            f"Distance: {trip['distance_km']:.3f} km"
        )
        print(
            f"Load: {trip['load_boxes']}/"
            f"{trip['capacity_boxes']} boxes "
            f"({trip['utilization_percent']:.1f}%)"
        )

    if result["gls_best_distance_km"] is not None:
        print("-" * 78)
        print(
            f"Best GLS distance       : "
            f"{result['gls_best_distance_km']:.3f} km"
        )
        print(
            f"Optimality gap          : "
            f"{result['optimality_gap_percent']:.3f}%"
        )
        print(
            f"GLS matches exact optimum: "
            f"{result['gls_matches_exact_optimum']}"
        )
    else:
        print("-" * 78)
        print(
            "GLS comparison was not calculated because the "
            "summary CSV was not found."
        )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Exact validation for the 13-node Gunadarma "
            "waste-collection CVRP."
        )
    )
    parser.add_argument(
        "--scenario",
        choices=["normal", "buffered", "peak", "all"],
        default="all",
        help="Scenario to validate. Default: all.",
    )
    parser.add_argument(
        "--gls-summary",
        type=Path,
        default=Path(
            "results/gls_experiments/"
            "gls_scenario_summary.csv"
        ),
        help=(
            "Repeated-run GLS summary CSV used to calculate "
            "the optimality gap."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/exact_validation"),
        help="Output directory.",
    )
    return parser.parse_args()


def main() -> None:
    validate_study_data()
    args = parse_arguments()

    scenarios = (
        ["normal", "buffered", "peak"]
        if args.scenario == "all"
        else [args.scenario]
    )

    distance_m = build_integer_distance_matrix()

    (
        tour_cost_m,
        tour_end_customer,
        parent,
    ) = held_karp_all_subsets(distance_m)

    gls_best_by_scenario = read_gls_summary(
        args.gls_summary
    )

    results: list[dict[str, Any]] = []

    for scenario in scenarios:
        exact_result = solve_exact_scenario(
            scenario=scenario,
            distance_m=distance_m,
            tour_cost_m=tour_cost_m,
            tour_end_customer=tour_end_customer,
            parent=parent,
        )

        exact_result = add_gls_comparison(
            exact_result,
            gls_best_by_scenario,
        )

        print_exact_result(exact_result)
        results.append(exact_result)

    summary_path = (
        args.output_dir
        / "exact_validation_summary.csv"
    )
    routes_path = (
        args.output_dir
        / "exact_validation_routes.json"
    )

    write_summary_csv(summary_path, results)
    write_json(routes_path, results)

    print("=" * 78)
    print("OUTPUT FILES")
    print("=" * 78)
    print(summary_path.resolve())
    print(routes_path.resolve())


if __name__ == "__main__":
    main()
