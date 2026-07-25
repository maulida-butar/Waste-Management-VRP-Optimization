"""
Project: Waste Management VRP Optimization - Universitas Gunadarma
File: Road_Distance_revised.py
Author: Maulida Boru Butar Butar

Purpose:
    Generates and audits the 13 x 13 directed road-distance matrix used by
    the waste-collection CVRP.

Key methodological rules:
    1. Reuse a frozen OpenStreetMap GraphML snapshot whenever available.
    2. Snap each campus to the road network once and export the snap audit.
    3. Preserve directionality. Distance(i, j) may differ from Distance(j, i).
    4. Never fabricate 0.2 km for duplicate snaps.
    5. Never replace unreachable paths with an arbitrary 999 km penalty.
    6. Export full-precision kilometres and rounded integer metres.
    7. Optionally compare the generated matrix against the matrix embedded
       in VRP_Solver_revised.py without importing OR-Tools.

Default outputs:
    data/gunadarma_drive_network.graphml
    results/road_distance/road_distance_matrix_km_full.csv
    results/road_distance/road_distance_matrix_m.csv
    results/road_distance/road_distance_matrix.json
    results/road_distance/road_distance_matrix_python.txt
    results/road_distance/campus_snapping_audit.csv
    results/road_distance/directed_pair_audit.csv
    results/road_distance/matrix_reference_comparison.csv
    results/road_distance/road_distance_metadata.json
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import platform
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import networkx as nx
import osmnx as ox
import pandas as pd
from pyproj import Transformer


LOCATIONS = [
    {"name": "D", "lat": -6.367957022267902, "lon": 106.83309635890863},
    {"name": "E", "lat": -6.353752172254033, "lon": 106.84159316305178},
    {"name": "G", "lat": -6.354234721369049, "lon": 106.84338356106764},
    {"name": "F4", "lat": -6.373649813990326, "lon": 106.86318582486531},
    {"name": "F5", "lat": -6.369296220683817, "lon": 106.83676819212762},
    {"name": "F6", "lat": -6.345757033149296, "lon": 106.85435354308778},
    {"name": "F7", "lat": -6.344363093455065, "lon": 106.88307686504615},
    {"name": "S", "lat": -6.296769680410338, "lon": 106.82973599992759},
    {"name": "C", "lat": -6.196973702159097, "lon": 106.85209241771877},
    {"name": "J1", "lat": -6.248946372849019, "lon": 106.97054774544556},
    {"name": "J3", "lat": -6.261687568292143, "lon": 107.02297516022837},
    {"name": "J6", "lat": -6.258541893722087, "lon": 106.95892368892778},
    {"name": "K", "lat": -6.232345261132437, "lon": 106.61554334227392},
]

NETWORK_TYPE = "drive"
EDGE_WEIGHT = "length"
DEFAULT_PADDING_DEGREES = 0.03
DEFAULT_MAX_SNAP_DISTANCE_M = 500.0
REFERENCE_MATRIX_VARIABLE = "DISTANCE_MATRIX_KM"


def configure_osmnx(timeout_seconds: int) -> None:
    """Configure OSMnx cache and request timeout."""
    ox.settings.use_cache = True
    ox.settings.timeout = timeout_seconds


def graph_from_bbox_compatible(
    west: float,
    south: float,
    east: float,
    north: float,
) -> nx.MultiDiGraph:
    """Download a driving graph with OSMnx 2.x/1.x compatibility."""
    bbox = (west, south, east, north)

    try:
        return ox.graph.graph_from_bbox(
            bbox=bbox,
            network_type=NETWORK_TYPE,
            simplify=True,
            retain_all=False,
            truncate_by_edge=True,
        )
    except (AttributeError, TypeError):
        try:
            return ox.graph_from_bbox(
                bbox=bbox,
                network_type=NETWORK_TYPE,
                simplify=True,
                retain_all=False,
                truncate_by_edge=True,
            )
        except TypeError:
            # Compatibility fallback for older OSMnx releases.
            return ox.graph_from_bbox(
                north,
                south,
                east,
                west,
                network_type=NETWORK_TYPE,
                simplify=True,
                retain_all=False,
                truncate_by_edge=True,
            )


def save_graphml_compatible(
    graph: nx.MultiDiGraph,
    graphml_path: Path,
) -> None:
    """Save GraphML using the public API available in the installed OSMnx."""
    graphml_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        ox.io.save_graphml(graph, filepath=graphml_path)
    except AttributeError:
        ox.save_graphml(graph, filepath=graphml_path)


def load_graphml_compatible(
    graphml_path: Path,
) -> nx.MultiDiGraph:
    """Load GraphML using the public API available in the installed OSMnx."""
    try:
        return ox.io.load_graphml(filepath=graphml_path)
    except AttributeError:
        return ox.load_graphml(filepath=graphml_path)


def project_graph_compatible(
    graph: nx.MultiDiGraph,
) -> nx.MultiDiGraph:
    """Project the graph to an appropriate local metric CRS."""
    try:
        return ox.projection.project_graph(graph)
    except AttributeError:
        return ox.project_graph(graph)


def calculate_bbox(
    padding_degrees: float,
) -> tuple[float, float, float, float]:
    """Calculate west, south, east, north bounds around all campuses."""
    latitudes = [item["lat"] for item in LOCATIONS]
    longitudes = [item["lon"] for item in LOCATIONS]

    return (
        min(longitudes) - padding_degrees,
        min(latitudes) - padding_degrees,
        max(longitudes) + padding_degrees,
        max(latitudes) + padding_degrees,
    )


def load_or_download_graph(
    graphml_path: Path,
    download_if_missing: bool,
    padding_degrees: float,
) -> tuple[nx.MultiDiGraph, str]:
    """
    Load a frozen graph. Download only when explicitly permitted.

    Returns:
        graph, graph_source
    """
    if graphml_path.exists():
        print(f"Loading frozen road network: {graphml_path.resolve()}")
        return load_graphml_compatible(graphml_path), "existing_graphml"

    if not download_if_missing:
        raise FileNotFoundError(
            f"Frozen GraphML file not found: {graphml_path}\n"
            "Run with --download-if-missing only when intentionally creating "
            "a new network snapshot."
        )

    west, south, east, north = calculate_bbox(padding_degrees)

    print("Downloading a new OpenStreetMap driving-network snapshot...")
    graph = graph_from_bbox_compatible(
        west=west,
        south=south,
        east=east,
        north=north,
    )

    save_graphml_compatible(graph, graphml_path)
    print(f"Frozen GraphML saved to: {graphml_path.resolve()}")

    return graph, "newly_downloaded_graphml"


def sha256_file(path: Path) -> str:
    """Return the SHA-256 checksum of a file."""
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def snap_campuses_once(
    projected_graph: nx.MultiDiGraph,
    max_snap_distance_m: float,
) -> tuple[list[Any], list[dict[str, Any]]]:
    """
    Project all campus coordinates and snap each campus to one graph node.

    The projected graph uses metre-based coordinates, allowing direct
    Euclidean auditing of point-to-node snap distance.
    """
    graph_crs = projected_graph.graph.get("crs")

    if graph_crs is None:
        raise ValueError("Projected graph has no CRS metadata.")

    transformer = Transformer.from_crs(
        "EPSG:4326",
        graph_crs,
        always_xy=True,
    )

    projected_x = []
    projected_y = []

    for location in LOCATIONS:
        x_value, y_value = transformer.transform(
            location["lon"],
            location["lat"],
        )
        projected_x.append(x_value)
        projected_y.append(y_value)

    snapped_nodes = ox.distance.nearest_nodes(
        projected_graph,
        X=projected_x,
        Y=projected_y,
    )

    # OSMnx returns a scalar for scalar input and a list/array for vectors.
    snapped_nodes = list(snapped_nodes)

    audit_rows: list[dict[str, Any]] = []

    for index, node_id in enumerate(snapped_nodes):
        node_data = projected_graph.nodes[node_id]
        node_x = float(node_data["x"])
        node_y = float(node_data["y"])
        snap_distance_m = math.hypot(
            projected_x[index] - node_x,
            projected_y[index] - node_y,
        )

        audit_rows.append(
            {
                "campus_index": index,
                "campus_name": LOCATIONS[index]["name"],
                "latitude": LOCATIONS[index]["lat"],
                "longitude": LOCATIONS[index]["lon"],
                "projected_x_m": projected_x[index],
                "projected_y_m": projected_y[index],
                "snapped_node_id": node_id,
                "node_x_m": node_x,
                "node_y_m": node_y,
                "snap_distance_m": snap_distance_m,
                "within_snap_threshold": (
                    snap_distance_m <= max_snap_distance_m
                ),
            }
        )

    excessive = [
        row
        for row in audit_rows
        if not row["within_snap_threshold"]
    ]

    if excessive:
        details = "; ".join(
            f"{row['campus_name']}={row['snap_distance_m']:.1f} m"
            for row in excessive
        )
        raise RuntimeError(
            "One or more campuses are too far from their snapped road node: "
            f"{details}. Increase the threshold only after manual inspection."
        )

    duplicate_groups: dict[Any, list[str]] = defaultdict(list)

    for row in audit_rows:
        duplicate_groups[row["snapped_node_id"]].append(
            row["campus_name"]
        )

    duplicate_groups = {
        node_id: campuses
        for node_id, campuses in duplicate_groups.items()
        if len(campuses) > 1
    }

    if duplicate_groups:
        details = "; ".join(
            f"node {node_id}: {', '.join(campuses)}"
            for node_id, campuses in duplicate_groups.items()
        )
        raise RuntimeError(
            "Distinct campuses snapped to the same road-network node. "
            "The previous script fabricated a 0.2 km distance in this case, "
            "which is not methodologically acceptable. Inspect or refine "
            f"the snapping procedure. Duplicate groups: {details}"
        )

    return snapped_nodes, audit_rows


def build_directed_distance_matrix(
    projected_graph: nx.MultiDiGraph,
    snapped_nodes: list[Any],
) -> list[list[float]]:
    """
    Build the full directed shortest-path matrix in metres.

    Unreachable pairs raise an error. No artificial 999 km penalty is used.
    """
    size = len(snapped_nodes)
    matrix_m = [
        [0.0 for _ in range(size)]
        for _ in range(size)
    ]

    print(f"Calculating a directed {size} x {size} road-distance matrix...")

    for origin_index, origin_node in enumerate(snapped_nodes):
        path_lengths = nx.single_source_dijkstra_path_length(
            projected_graph,
            source=origin_node,
            weight=EDGE_WEIGHT,
        )

        for destination_index, destination_node in enumerate(snapped_nodes):
            if origin_index == destination_index:
                matrix_m[origin_index][destination_index] = 0.0
                continue

            if destination_node not in path_lengths:
                raise nx.NetworkXNoPath(
                    "No directed road path from "
                    f"{LOCATIONS[origin_index]['name']} "
                    f"(node {origin_node}) to "
                    f"{LOCATIONS[destination_index]['name']} "
                    f"(node {destination_node})."
                )

            distance_m = float(path_lengths[destination_node])

            if distance_m <= 0:
                raise RuntimeError(
                    "A non-diagonal road distance is non-positive for "
                    f"{LOCATIONS[origin_index]['name']} -> "
                    f"{LOCATIONS[destination_index]['name']}: "
                    f"{distance_m} m."
                )

            matrix_m[origin_index][destination_index] = distance_m

    return matrix_m


def audit_directed_pairs(
    matrix_m: list[list[float]],
    snapped_nodes: list[Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Create pair-level directionality and asymmetry diagnostics."""
    rows: list[dict[str, Any]] = []
    unordered_differences_m: list[float] = []
    asymmetric_pairs_over_1m = 0

    size = len(matrix_m)

    for origin in range(size):
        for destination in range(size):
            if origin == destination:
                continue

            forward_m = matrix_m[origin][destination]
            reverse_m = matrix_m[destination][origin]
            difference_m = forward_m - reverse_m

            rows.append(
                {
                    "origin_index": origin,
                    "origin_name": LOCATIONS[origin]["name"],
                    "destination_index": destination,
                    "destination_name": LOCATIONS[destination]["name"],
                    "origin_node_id": snapped_nodes[origin],
                    "destination_node_id": snapped_nodes[destination],
                    "distance_m_full": forward_m,
                    "distance_m_rounded": round(forward_m),
                    "distance_km_full": forward_m / 1000,
                    "reverse_distance_m_full": reverse_m,
                    "signed_asymmetry_m": difference_m,
                    "absolute_asymmetry_m": abs(difference_m),
                }
            )

    for first in range(size):
        for second in range(first + 1, size):
            absolute_difference = abs(
                matrix_m[first][second]
                - matrix_m[second][first]
            )
            unordered_differences_m.append(absolute_difference)

            if absolute_difference > 1.0:
                asymmetric_pairs_over_1m += 1

    summary = {
        "directed_non_diagonal_pairs": size * (size - 1),
        "unordered_node_pairs": size * (size - 1) // 2,
        "unordered_pairs_asymmetric_over_1m": asymmetric_pairs_over_1m,
        "mean_absolute_asymmetry_m": (
            sum(unordered_differences_m)
            / len(unordered_differences_m)
        ),
        "maximum_absolute_asymmetry_m": max(unordered_differences_m),
    }

    return rows, summary


def load_literal_from_python(
    python_path: Path,
    variable_name: str,
) -> Any:
    """
    Read a literal assignment from a Python source file without importing it.

    This avoids importing OR-Tools merely to audit the embedded matrix.
    """
    syntax_tree = ast.parse(
        python_path.read_text(encoding="utf-8"),
        filename=str(python_path),
    )

    for node in syntax_tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == variable_name
                ):
                    return ast.literal_eval(node.value)

        if isinstance(node, ast.AnnAssign):
            if (
                isinstance(node.target, ast.Name)
                and node.target.id == variable_name
                and node.value is not None
            ):
                return ast.literal_eval(node.value)

    raise ValueError(
        f"Variable '{variable_name}' was not found as a literal assignment "
        f"in {python_path}."
    )


def compare_with_reference_matrix(
    generated_matrix_m: list[list[float]],
    reference_solver_path: Path,
    tolerance_m: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]] | None:
    """Compare the new matrix with the matrix embedded in the solver."""
    if not reference_solver_path.exists():
        return None

    reference_matrix_km = load_literal_from_python(
        reference_solver_path,
        REFERENCE_MATRIX_VARIABLE,
    )

    size = len(LOCATIONS)

    if (
        len(reference_matrix_km) != size
        or any(len(row) != size for row in reference_matrix_km)
    ):
        raise ValueError(
            "Reference distance matrix dimensions do not match the study."
        )

    rows: list[dict[str, Any]] = []
    absolute_differences_m: list[float] = []
    mismatched_pairs = 0

    for origin in range(size):
        for destination in range(size):
            generated_m = generated_matrix_m[origin][destination]
            reference_m = (
                float(reference_matrix_km[origin][destination])
                * 1000
            )
            absolute_difference_m = abs(generated_m - reference_m)

            if absolute_difference_m > tolerance_m:
                mismatched_pairs += 1

            absolute_differences_m.append(absolute_difference_m)

            rows.append(
                {
                    "origin_name": LOCATIONS[origin]["name"],
                    "destination_name": LOCATIONS[destination]["name"],
                    "generated_distance_m_full": generated_m,
                    "reference_distance_m_full": reference_m,
                    "signed_difference_m": generated_m - reference_m,
                    "absolute_difference_m": absolute_difference_m,
                    "within_tolerance": (
                        absolute_difference_m <= tolerance_m
                    ),
                }
            )

    summary = {
        "reference_solver_path": str(reference_solver_path.resolve()),
        "reference_variable": REFERENCE_MATRIX_VARIABLE,
        "tolerance_m": tolerance_m,
        "matrix_cells_compared": size * size,
        "cells_outside_tolerance": mismatched_pairs,
        "maximum_absolute_difference_m": max(absolute_differences_m),
        "mean_absolute_difference_m": (
            sum(absolute_differences_m)
            / len(absolute_differences_m)
        ),
        "exact_snapshot_match": mismatched_pairs == 0,
    }

    return rows, summary


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    """Write dictionaries to UTF-8 CSV."""
    if not rows:
        raise ValueError(f"No rows supplied for {path}.")

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)


def export_matrices(
    output_dir: Path,
    matrix_m: list[list[float]],
) -> dict[str, Path]:
    """Export full-precision kilometres and rounded integer metres."""
    names = [item["name"] for item in LOCATIONS]

    matrix_km = [
        [value / 1000 for value in row]
        for row in matrix_m
    ]
    matrix_integer_m = [
        [round(value) for value in row]
        for row in matrix_m
    ]

    kilometre_csv = (
        output_dir
        / "road_distance_matrix_km_full.csv"
    )
    metre_csv = (
        output_dir
        / "road_distance_matrix_m.csv"
    )
    json_path = (
        output_dir
        / "road_distance_matrix.json"
    )
    python_path = (
        output_dir
        / "road_distance_matrix_python.txt"
    )

    pd.DataFrame(
        matrix_km,
        index=names,
        columns=names,
    ).to_csv(
        kilometre_csv,
        encoding="utf-8-sig",
        float_format="%.12f",
    )

    pd.DataFrame(
        matrix_integer_m,
        index=names,
        columns=names,
    ).to_csv(
        metre_csv,
        encoding="utf-8-sig",
    )

    json_payload = {
        "node_names": names,
        "units": {
            "full_precision_matrix": "kilometres",
            "optimization_matrix": "integer metres",
        },
        "distance_matrix_km_full": matrix_km,
        "distance_matrix_m_integer": matrix_integer_m,
    }
    json_path.write_text(
        json.dumps(
            json_payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    python_literal = (
        "DISTANCE_MATRIX_KM = "
        + json.dumps(matrix_km, indent=4)
        + "\n\n"
        "DISTANCE_MATRIX_M = "
        + json.dumps(matrix_integer_m, indent=4)
        + "\n"
    )
    python_path.write_text(
        python_literal,
        encoding="utf-8",
    )

    return {
        "kilometre_csv": kilometre_csv,
        "metre_csv": metre_csv,
        "json": json_path,
        "python_literal": python_path,
    }


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate and audit the directed Gunadarma road-distance matrix."
        )
    )
    parser.add_argument(
        "--graphml",
        type=Path,
        default=Path(
            "data/gunadarma_drive_network.graphml"
        ),
        help="Frozen GraphML network snapshot.",
    )
    parser.add_argument(
        "--download-if-missing",
        action="store_true",
        help=(
            "Download and freeze a new OSM network only when GraphML is absent."
        ),
    )
    parser.add_argument(
        "--padding",
        type=float,
        default=DEFAULT_PADDING_DEGREES,
        help="Bounding-box padding in degrees for a new download.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="OSMnx request timeout in seconds.",
    )
    parser.add_argument(
        "--max-snap-distance-m",
        type=float,
        default=DEFAULT_MAX_SNAP_DISTANCE_M,
        help=(
            "Maximum permitted campus-to-node snap distance in metres."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(
            "results/road_distance"
        ),
        help="Output directory.",
    )
    parser.add_argument(
        "--reference-solver",
        type=Path,
        default=Path(
            "VRP_Solver_revised.py"
        ),
        help=(
            "Optional solver source containing DISTANCE_MATRIX_KM."
        ),
    )
    parser.add_argument(
        "--reference-tolerance-m",
        type=float,
        default=1.0,
        help=(
            "Permitted cell difference when comparing against the "
            "embedded solver matrix."
        ),
    )
    parser.add_argument(
        "--fail-on-reference-mismatch",
        action="store_true",
        help=(
            "Stop with an error if the generated matrix differs from "
            "the reference matrix beyond tolerance."
        ),
    )
    return parser.parse_args()


def main() -> None:
    """Generate, validate, compare, and export the road matrix."""
    args = parse_arguments()

    if args.padding <= 0:
        raise ValueError("--padding must be greater than zero.")

    if args.timeout <= 0:
        raise ValueError("--timeout must be greater than zero.")

    if args.max_snap_distance_m <= 0:
        raise ValueError(
            "--max-snap-distance-m must be greater than zero."
        )

    configure_osmnx(args.timeout)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    graph_raw, graph_source = load_or_download_graph(
        graphml_path=args.graphml,
        download_if_missing=args.download_if_missing,
        padding_degrees=args.padding,
    )

    if not nx.is_directed(graph_raw):
        raise ValueError(
            "The loaded road network is not directed."
        )

    graph_projected = project_graph_compatible(graph_raw)

    snapped_nodes, snapping_audit = snap_campuses_once(
        projected_graph=graph_projected,
        max_snap_distance_m=args.max_snap_distance_m,
    )

    matrix_m = build_directed_distance_matrix(
        projected_graph=graph_projected,
        snapped_nodes=snapped_nodes,
    )

    pair_rows, asymmetry_summary = audit_directed_pairs(
        matrix_m=matrix_m,
        snapped_nodes=snapped_nodes,
    )

    matrix_paths = export_matrices(
        output_dir=args.output_dir,
        matrix_m=matrix_m,
    )

    snapping_path = (
        args.output_dir
        / "campus_snapping_audit.csv"
    )
    pair_audit_path = (
        args.output_dir
        / "directed_pair_audit.csv"
    )

    write_csv(snapping_path, snapping_audit)
    write_csv(pair_audit_path, pair_rows)

    reference_comparison = compare_with_reference_matrix(
        generated_matrix_m=matrix_m,
        reference_solver_path=args.reference_solver,
        tolerance_m=args.reference_tolerance_m,
    )

    reference_summary = None
    reference_comparison_path = (
        args.output_dir
        / "matrix_reference_comparison.csv"
    )

    if reference_comparison is not None:
        reference_rows, reference_summary = reference_comparison
        write_csv(
            reference_comparison_path,
            reference_rows,
        )

        if not reference_summary["exact_snapshot_match"]:
            print(
                "WARNING: the generated matrix does not exactly match the "
                "matrix embedded in the solver."
            )
            print(
                "Maximum absolute difference: "
                f"{reference_summary['maximum_absolute_difference_m']:.3f} m"
            )
            print(
                "This indicates that the frozen GraphML snapshot, snapping "
                "configuration, or network-processing workflow differs from "
                "the one used to create the solver matrix."
            )

            if args.fail_on_reference_mismatch:
                raise RuntimeError(
                    "Reference-matrix comparison failed."
                )
        else:
            print(
                "Reference audit passed: generated and embedded matrices "
                "match within the configured tolerance."
            )
    else:
        print(
            f"Reference solver not found at {args.reference_solver}; "
            "matrix comparison was skipped."
        )

    graph_checksum = (
        sha256_file(args.graphml)
        if args.graphml.exists()
        else None
    )

    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "project": (
            "Universitas Gunadarma institutional waste-collection CVRP"
        ),
        "method": (
            "Directed shortest-path distance on a frozen OSM driving network"
        ),
        "edge_weight": EDGE_WEIGHT,
        "edge_weight_units": "metres",
        "optimization_conversion": (
            "Each full-precision path length is rounded to the nearest "
            "integer metre."
        ),
        "graph": {
            "source": graph_source,
            "graphml_path": str(args.graphml.resolve()),
            "graphml_sha256": graph_checksum,
            "network_type": NETWORK_TYPE,
            "raw_crs": str(graph_raw.graph.get("crs")),
            "projected_crs": str(
                graph_projected.graph.get("crs")
            ),
            "directed": nx.is_directed(graph_raw),
            "raw_node_count": graph_raw.number_of_nodes(),
            "raw_edge_count": graph_raw.number_of_edges(),
        },
        "bbox": {
            "west_south_east_north": calculate_bbox(
                args.padding
            ),
            "padding_degrees": args.padding,
        },
        "snapping": {
            "method": "nearest road-network node after graph projection",
            "maximum_allowed_snap_distance_m": (
                args.max_snap_distance_m
            ),
            "maximum_observed_snap_distance_m": max(
                row["snap_distance_m"]
                for row in snapping_audit
            ),
            "duplicate_snapped_nodes": False,
        },
        "matrix": {
            "node_count_including_depot": len(LOCATIONS),
            "collection_node_count": len(LOCATIONS) - 1,
            "directed": True,
            **asymmetry_summary,
        },
        "reference_comparison": reference_summary,
        "software": {
            "python_version": platform.python_version(),
            "osmnx_version": getattr(
                ox,
                "__version__",
                "unknown",
            ),
            "networkx_version": nx.__version__,
            "pandas_version": pd.__version__,
        },
        "outputs": {
            key: str(output_path.resolve())
            for key, output_path in {
                **matrix_paths,
                "snapping_audit": snapping_path,
                "directed_pair_audit": pair_audit_path,
                **(
                    {
                        "reference_comparison": (
                            reference_comparison_path
                        )
                    }
                    if reference_comparison is not None
                    else {}
                ),
            }.items()
        },
    }

    metadata_path = (
        args.output_dir
        / "road_distance_metadata.json"
    )
    metadata_path.write_text(
        json.dumps(
            metadata,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )

    print("=" * 78)
    print("ROAD-DISTANCE MATRIX GENERATION COMPLETED")
    print("=" * 78)
    print(f"Graph source              : {graph_source}")
    print(f"GraphML SHA-256           : {graph_checksum}")
    print(
        "Maximum snap distance    : "
        f"{metadata['snapping']['maximum_observed_snap_distance_m']:.3f} m"
    )
    print(
        "Asymmetric unordered pairs: "
        f"{asymmetry_summary['unordered_pairs_asymmetric_over_1m']}/"
        f"{asymmetry_summary['unordered_node_pairs']}"
    )
    print(
        "Mean absolute asymmetry  : "
        f"{asymmetry_summary['mean_absolute_asymmetry_m']:.3f} m"
    )
    print("-" * 78)

    for path in [
        matrix_paths["kilometre_csv"],
        matrix_paths["metre_csv"],
        matrix_paths["json"],
        matrix_paths["python_literal"],
        snapping_path,
        pair_audit_path,
        metadata_path,
    ]:
        print(path.resolve())

    if reference_comparison is not None:
        print(reference_comparison_path.resolve())


if __name__ == "__main__":
    main()
