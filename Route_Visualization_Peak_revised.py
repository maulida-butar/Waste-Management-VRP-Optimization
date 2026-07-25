"""
Project: Waste Management VRP Optimization - Universitas Gunadarma
File: Route_Visualization_Peak_revised.py
Author: Maulida Boru Butar Butar

Purpose:
    Produces publication-quality and interactive visualizations of the
    exact-optimal Peak scenario using actual OpenStreetMap road geometry.

Outputs:
    figures/peak_route_network_600dpi.png
    figures/peak_route_network.pdf
    figures/peak_route_network.svg
    figures/peak_route_interactive.html
    figures/peak_route_geometry.geojson

Important:
    For strict reproducibility, use the same frozen GraphML file that was
    used to generate the published directed distance matrix. If the GraphML
    file is missing, this script can download a new OSM network, but the
    resulting road geometry may differ from the manuscript snapshot.
"""

from __future__ import annotations

import argparse
import math
import json
from pathlib import Path
from typing import Any

import folium
import matplotlib.pyplot as plt
import networkx as nx
import osmnx as ox
from folium.features import DivIcon
from shapely.geometry import LineString, mapping


def import_study_data() -> tuple[
    list[str],
    list[tuple[float, float]],
    list[list[float]],
]:
    """Import names, coordinates, and the fixed directed distance matrix."""
    try:
        from VRP_Solver_revised import (
            NODE_NAMES,
            DISTANCE_MATRIX_KM,
        )
    except ImportError:
        try:
            from VRP_Solver import (
                NODE_NAMES,
                DISTANCE_MATRIX_KM,
            )
        except ImportError as exc:
            raise ImportError(
                "Place this script in the same folder as "
                "VRP_Solver_revised.py, or rename the revised solver "
                "to VRP_Solver.py."
            ) from exc

    coordinates = [
        (-6.367957022267902, 106.83309635890863),  # D
        (-6.353752172254033, 106.84159316305178),  # E
        (-6.354234721369049, 106.84338356106764),  # G
        (-6.373649813990326, 106.86318582486531),  # F4
        (-6.369296220683817, 106.83676819212762),  # F5
        (-6.345757033149296, 106.85435354308778),  # F6
        (-6.344363093455065, 106.88307686504615),  # F7
        (-6.296769680410338, 106.82973599992759),  # S
        (-6.196973702159097, 106.85209241771877),  # C
        (-6.248946372849019, 106.97054774544556),  # J1
        (-6.261687568292143, 107.02297516022837),  # J3
        (-6.258541893722087, 106.95892368892778),  # J6
        (-6.232345261132437, 106.61554334227392),  # K
    ]

    return NODE_NAMES, coordinates, DISTANCE_MATRIX_KM


NODE_NAMES, COORDINATES, DISTANCE_MATRIX_KM = import_study_data()

# Central depot is Campus D at node index 0.
DEPOT_INDEX = 0

# Exact-optimal Peak solution.
PEAK_TRIPS = [
    {
        "trip_id": 1,
        "route": [0, 4, 0],
        "load_boxes": 18,
        "distance_km": 5.586,
        "label": "Trip 1: F5 shuttle",
    },
    {
        "trip_id": 2,
        "route": [0, 2, 1, 5, 3, 6, 9, 10, 11, 8, 12, 7, 0],
        "load_boxes": 173,
        "distance_km": 142.751,
        "label": "Trip 2: main loop",
    },
]


def validate_routes() -> None:
    """Check route totals against the fixed directed matrix."""
    for trip in PEAK_TRIPS:
        route = trip["route"]
        calculated = sum(
            round(DISTANCE_MATRIX_KM[route[i]][route[i + 1]] * 1000)
            for i in range(len(route) - 1)
        ) / 1000

        if abs(calculated - trip["distance_km"]) > 0.001:
            raise ValueError(
                f"Distance audit failed for Trip {trip['trip_id']}: "
                f"expected {trip['distance_km']:.3f} km, "
                f"calculated {calculated:.3f} km."
            )


def download_graph(graphml_path: Path, padding: float = 0.03) -> nx.MultiDiGraph:
    """Download the driving network covering all study nodes."""
    lats = [lat for lat, _ in COORDINATES]
    lons = [lon for _, lon in COORDINATES]

    west = min(lons) - padding
    south = min(lats) - padding
    east = max(lons) + padding
    north = max(lats) + padding

    print("Downloading the OpenStreetMap driving network...")

    try:
        # OSMnx 2.x
        graph = ox.graph_from_bbox(
            bbox=(west, south, east, north),
            network_type="drive",
            simplify=True,
            retain_all=False,
        )
    except TypeError:
        # Compatibility fallback for older OSMnx versions.
        graph = ox.graph_from_bbox(
            north,
            south,
            east,
            west,
            network_type="drive",
            simplify=True,
            retain_all=False,
        )

    graphml_path.parent.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(graph, graphml_path)
    print(f"Graph saved to: {graphml_path.resolve()}")
    print(
        "Warning: this is a newly downloaded OSM network. "
        "For the manuscript, preserve and reuse this GraphML file."
    )
    return graph


def load_or_download_graph(
    graphml_path: Path,
    download_if_missing: bool = True,
) -> nx.MultiDiGraph:
    """
    Load a frozen GraphML road network.

    If the file does not exist, the script automatically downloads the
    OpenStreetMap driving network, saves it as GraphML, and reuses that
    frozen file on subsequent runs.
    """
    if graphml_path.exists():
        print(f"Loading frozen road network: {graphml_path.resolve()}")
        return ox.load_graphml(graphml_path)

    print(
        f"GraphML file not found: {graphml_path}. "
        "Downloading and freezing the road network now..."
    )
    return download_graph(graphml_path)


def nearest_graph_nodes(graph: nx.MultiDiGraph) -> dict[int, int]:
    """Snap every campus coordinate to its nearest road-network node."""
    snapped: dict[int, int] = {}

    for index, (lat, lon) in enumerate(COORDINATES):
        snapped[index] = ox.distance.nearest_nodes(
            graph,
            X=lon,
            Y=lat,
        )

    return snapped


def shortest_path_nodes(
    graph: nx.MultiDiGraph,
    origin_node: int,
    destination_node: int,
) -> list[int]:
    """Return one directed shortest path based on edge length."""
    try:
        return nx.shortest_path(
            graph,
            source=origin_node,
            target=destination_node,
            weight="length",
        )
    except nx.NetworkXNoPath as exc:
        raise RuntimeError(
            f"No directed road path exists from {origin_node} "
            f"to {destination_node}."
        ) from exc


def select_shortest_parallel_edge(
    graph: nx.MultiDiGraph,
    u: int,
    v: int,
) -> dict[str, Any]:
    """Select the shortest edge when multiple parallel edges exist."""
    edge_dict = graph.get_edge_data(u, v)

    if not edge_dict:
        raise RuntimeError(f"Missing edge data for {u} -> {v}.")

    return min(
        edge_dict.values(),
        key=lambda attributes: float(
            attributes.get("length", float("inf"))
        ),
    )


def edge_coordinates(
    graph: nx.MultiDiGraph,
    u: int,
    v: int,
) -> list[tuple[float, float]]:
    """
    Return ordered (longitude, latitude) coordinates for one graph edge.
    """
    attributes = select_shortest_parallel_edge(graph, u, v)

    if "geometry" in attributes:
        coordinates = list(attributes["geometry"].coords)
    else:
        coordinates = [
            (graph.nodes[u]["x"], graph.nodes[u]["y"]),
            (graph.nodes[v]["x"], graph.nodes[v]["y"]),
        ]

    u_xy = (graph.nodes[u]["x"], graph.nodes[u]["y"])

    first_distance = (
        (coordinates[0][0] - u_xy[0]) ** 2
        + (coordinates[0][1] - u_xy[1]) ** 2
    )
    last_distance = (
        (coordinates[-1][0] - u_xy[0]) ** 2
        + (coordinates[-1][1] - u_xy[1]) ** 2
    )

    if last_distance < first_distance:
        coordinates.reverse()

    return coordinates


def path_geometry(
    graph: nx.MultiDiGraph,
    path_nodes: list[int],
) -> list[tuple[float, float]]:
    """Convert a road-network node path to ordered lon-lat coordinates."""
    all_coordinates: list[tuple[float, float]] = []

    for u, v in zip(path_nodes[:-1], path_nodes[1:]):
        segment = edge_coordinates(graph, u, v)

        if all_coordinates and segment:
            segment = segment[1:]

        all_coordinates.extend(segment)

    return all_coordinates


def build_trip_geometry(
    graph: nx.MultiDiGraph,
    snapped_nodes: dict[int, int],
    campus_route: list[int],
) -> list[tuple[float, float]]:
    """Build the complete actual-road geometry for one campus route."""
    route_coordinates: list[tuple[float, float]] = []

    for origin, destination in zip(
        campus_route[:-1],
        campus_route[1:],
    ):
        network_path = shortest_path_nodes(
            graph,
            snapped_nodes[origin],
            snapped_nodes[destination],
        )
        segment_coordinates = path_geometry(graph, network_path)

        if route_coordinates and segment_coordinates:
            segment_coordinates = segment_coordinates[1:]

        route_coordinates.extend(segment_coordinates)

    return route_coordinates


def export_geojson(
    output_path: Path,
    trip_geometries: list[dict[str, Any]],
) -> None:
    """Export actual road geometries as GeoJSON."""
    features = []

    for trip in trip_geometries:
        line = LineString(trip["geometry_lon_lat"])
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "trip_id": trip["trip_id"],
                    "label": trip["label"],
                    "distance_km": trip["distance_km"],
                    "load_boxes": trip["load_boxes"],
                    "route": " -> ".join(
                        NODE_NAMES[node]
                        for node in trip["route"]
                    ),
                },
                "geometry": mapping(line),
            }
        )

    feature_collection = {
        "type": "FeatureCollection",
        "features": features,
    }

    output_path.write_text(
        json.dumps(feature_collection, indent=2),
        encoding="utf-8",
    )


def create_interactive_map(
    output_path: Path,
    trip_geometries: list[dict[str, Any]],
) -> None:
    """Create an interactive HTML map using actual road geometry."""
    route_map = folium.Map(
        location=COORDINATES[0],
        zoom_start=10,
        tiles="CartoDB positron",
        control_scale=True,
    )

    folium.TileLayer(
        tiles="OpenStreetMap",
        name="OpenStreetMap",
        control=True,
    ).add_to(route_map)

    route_styles = {
        1: {"color": "#d95f02", "weight": 7},
        2: {"color": "#6a3d9a", "weight": 5},
    }

    # Draw routes first so markers remain visible.
    for trip in sorted(
        trip_geometries,
        key=lambda item: item["trip_id"],
        reverse=True,
    ):
        style = route_styles[trip["trip_id"]]
        folium.PolyLine(
            locations=[
                (lat, lon)
                for lon, lat in trip["geometry_lon_lat"]
            ],
            color=style["color"],
            weight=style["weight"],
            opacity=0.88,
            tooltip=(
                f"{trip['label']} | "
                f"{trip['distance_km']:.3f} km | "
                f"{trip['load_boxes']} boxes"
            ),
        ).add_to(route_map)

    for node_index, (lat, lon) in enumerate(COORDINATES):
        is_depot = node_index == DEPOT_INDEX

        folium.CircleMarker(
            location=(lat, lon),
            radius=8 if is_depot else 6,
            color="#000000",
            weight=1,
            fill=True,
            fill_color="#d73027" if is_depot else "#ffffff",
            fill_opacity=1.0,
            tooltip=NODE_NAMES[node_index],
            popup=(
                f"<b>{NODE_NAMES[node_index]}</b><br>"
                f"{'Central depot' if is_depot else 'Collection node'}"
            ),
        ).add_to(route_map)

        folium.Marker(
            location=(lat, lon),
            icon=DivIcon(
                icon_size=(80, 24),
                icon_anchor=(-6, 10),
                html=(
                    "<div style='font-size:11px;font-weight:bold;"
                    "color:#111;background:rgba(255,255,255,0.78);"
                    "padding:1px 3px;border-radius:2px;'>"
                    f"{NODE_NAMES[node_index]}</div>"
                ),
            ),
        ).add_to(route_map)

    legend_html = """
    <div style="
        position: fixed;
        bottom: 38px;
        left: 38px;
        width: 285px;
        z-index: 9999;
        background: rgba(255,255,255,0.94);
        border: 1px solid #555;
        padding: 10px 12px;
        font-size: 13px;
        line-height: 1.5;">
        <b>Peak scenario: exact-optimal solution</b><br>
        <span style="display:inline-block;width:20px;height:4px;
                     background:#d95f02;margin-right:6px;"></span>
        Trip 1: D–F5–D, 5.586 km, 18 boxes<br>
        <span style="display:inline-block;width:20px;height:4px;
                     background:#6a3d9a;margin-right:6px;"></span>
        Trip 2: main loop, 142.751 km, 173 boxes<br>
        <b>Total: 148.337 km</b><br>
        <span style="font-size:11px;">
        Map data © OpenStreetMap contributors
        </span>
    </div>
    """
    route_map.get_root().html.add_child(
        folium.Element(legend_html)
    )
    folium.LayerControl(collapsed=True).add_to(route_map)

    route_map.save(output_path)



def add_direction_arrows(
    ax: Any,
    geometry_lon_lat: list[tuple[float, float]],
    color: str,
    fractions: tuple[float, ...],
    zorder: int,
) -> None:
    """Add directional arrows along a route without excessive clutter."""
    if len(geometry_lon_lat) < 3:
        return

    segment_lengths = []
    total_length = 0.0

    for start, end in zip(
        geometry_lon_lat[:-1],
        geometry_lon_lat[1:],
    ):
        length = math.hypot(
            end[0] - start[0],
            end[1] - start[1],
        )
        segment_lengths.append(length)
        total_length += length

    if total_length == 0:
        return

    for fraction in fractions:
        target = total_length * fraction
        accumulated = 0.0

        for index, segment_length in enumerate(segment_lengths):
            if accumulated + segment_length >= target:
                start = geometry_lon_lat[index]
                end = geometry_lon_lat[index + 1]

                if segment_length == 0:
                    break

                local_fraction = (
                    target - accumulated
                ) / segment_length

                arrow_end = (
                    start[0]
                    + (end[0] - start[0]) * local_fraction,
                    start[1]
                    + (end[1] - start[1]) * local_fraction,
                )

                back_fraction = max(
                    0.0,
                    local_fraction - 0.55,
                )
                arrow_start = (
                    start[0]
                    + (end[0] - start[0]) * back_fraction,
                    start[1]
                    + (end[1] - start[1]) * back_fraction,
                )

                ax.annotate(
                    "",
                    xy=arrow_end,
                    xytext=arrow_start,
                    arrowprops={
                        "arrowstyle": "-|>",
                        "color": color,
                        "lw": 1.4,
                        "mutation_scale": 12,
                        "shrinkA": 0,
                        "shrinkB": 0,
                    },
                    zorder=zorder,
                )
                break

            accumulated += segment_length


def add_scale_bar(
    ax: Any,
    length_km: float = 10.0,
) -> None:
    """Add an approximate scale bar for a geographic lon-lat plot."""
    mean_latitude = sum(
        latitude for latitude, _ in COORDINATES
    ) / len(COORDINATES)

    kilometres_per_degree_lon = (
        111.32 * math.cos(math.radians(mean_latitude))
    )
    longitude_length = (
        length_km / kilometres_per_degree_lon
    )

    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()

    x_start = x_min + 0.055 * (x_max - x_min)
    y_start = y_min + 0.075 * (y_max - y_min)
    tick_height = 0.012 * (y_max - y_min)

    ax.plot(
        [x_start, x_start + longitude_length],
        [y_start, y_start],
        color="black",
        linewidth=2.2,
        zorder=12,
    )
    ax.plot(
        [x_start, x_start],
        [y_start - tick_height, y_start + tick_height],
        color="black",
        linewidth=1.5,
        zorder=12,
    )
    ax.plot(
        [
            x_start + longitude_length,
            x_start + longitude_length,
        ],
        [y_start - tick_height, y_start + tick_height],
        color="black",
        linewidth=1.5,
        zorder=12,
    )
    ax.text(
        x_start + longitude_length / 2,
        y_start + 1.7 * tick_height,
        f"{length_km:g} km",
        ha="center",
        va="bottom",
        fontsize=8.5,
        bbox={
            "facecolor": "white",
            "edgecolor": "none",
            "alpha": 0.82,
            "pad": 1.5,
        },
        zorder=13,
    )


def create_static_figure(
    output_dir: Path,
    graph: nx.MultiDiGraph,
    trip_geometries: list[dict[str, Any]],
) -> None:
    """Create publication-quality PNG, PDF, and SVG figures."""
    fig, ax = plt.subplots(figsize=(13, 9))

    # Plot the underlying directed road network.
    ox.plot_graph(
        graph,
        ax=ax,
        node_size=0,
        edge_linewidth=0.18,
        edge_color="#dddddd",
        bgcolor="white",
        show=False,
        close=False,
    )

    route_styles = {
        1: {
            "color": "#d95f02",
            "linewidth": 7.0,
            "label": "Trip 1: D–F5–D (5.586 km; 18 boxes)",
            "zorder": 7,
        },
        2: {
            "color": "#6a3d9a",
            "linewidth": 3.0,
            "label": "Trip 2: main loop (142.751 km; 173 boxes)",
            "zorder": 5,
        },
    }

    for trip in sorted(
        trip_geometries,
        key=lambda item: item["trip_id"],
        reverse=True,
    ):
        style = route_styles[trip["trip_id"]]
        xs = [point[0] for point in trip["geometry_lon_lat"]]
        ys = [point[1] for point in trip["geometry_lon_lat"]]

        ax.plot(
            xs,
            ys,
            color=style["color"],
            linewidth=style["linewidth"],
            alpha=0.90,
            label=style["label"],
            zorder=style["zorder"],
        )

        add_direction_arrows(
            ax=ax,
            geometry_lon_lat=trip["geometry_lon_lat"],
            color=style["color"],
            fractions=(0.50,)
            if trip["trip_id"] == 1
            else (0.18, 0.43, 0.68, 0.88),
            zorder=style["zorder"] + 1,
        )

    # Plot and label campus nodes.
    label_offsets = {
        0: (-5, 11),   # D
        1: (8, 12),    # E
        2: (8, -13),   # G
        3: (7, -13),   # F4
        4: (9, -3),    # F5
        5: (5, 8),     # F6
        6: (5, 8),     # F7
        7: (5, 6),     # S
        8: (5, 6),     # C
        9: (5, 6),     # J1
        10: (5, 6),    # J3
        11: (5, 6),    # J6
        12: (5, 6),    # K
    }

    for node_index, (lat, lon) in enumerate(COORDINATES):
        is_depot = node_index == DEPOT_INDEX

        ax.scatter(
            lon,
            lat,
            s=75 if is_depot else 42,
            marker="s" if is_depot else "o",
            facecolor="#d73027" if is_depot else "white",
            edgecolor="black",
            linewidth=0.9,
            zorder=8,
        )

        ax.annotate(
            NODE_NAMES[node_index],
            xy=(lon, lat),
            xytext=label_offsets[node_index],
            textcoords="offset points",
            fontsize=9,
            fontweight="bold",
            bbox={
                "boxstyle": "round,pad=0.18",
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.80,
            },
            zorder=9,
        )

    ax.set_title(
        "Exact-optimal routes under the peak-demand scenario",
        fontsize=12.5,
        pad=12,
    )

    ax.legend(
        loc="lower right",
        frameon=True,
        framealpha=0.97,
        fontsize=8.8,
        title="Peak scenario: total distance 148.337 km",
        title_fontsize=9.2,
    )

    # North arrow.
    ax.annotate(
        "N",
        xy=(0.965, 0.92),
        xytext=(0.965, 0.82),
        xycoords="axes fraction",
        textcoords="axes fraction",
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        arrowprops={
            "facecolor": "black",
            "width": 2,
            "headwidth": 8,
        },
    )

    fig.text(
        0.01,
        0.012,
        "Road-network data © OpenStreetMap contributors. "
        "Routes generated by the authors using OSMnx and NetworkX.",
        fontsize=7.5,
        ha="left",
        va="bottom",
    )

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")

    # Focus the map on study nodes while retaining some margin.
    lats = [lat for lat, _ in COORDINATES]
    lons = [lon for _, lon in COORDINATES]
    lon_margin = (max(lons) - min(lons)) * 0.08
    lat_margin = (max(lats) - min(lats)) * 0.10
    ax.set_xlim(min(lons) - lon_margin, max(lons) + lon_margin)
    ax.set_ylim(min(lats) - lat_margin, max(lats) + lat_margin)

    add_scale_bar(ax, length_km=10.0)

    fig.tight_layout(rect=[0, 0.025, 1, 1])

    fig.savefig(
        output_dir / "peak_route_network_edited_600dpi.png",
        dpi=600,
        bbox_inches="tight",
        pad_inches=0.05
    )
    fig.savefig(
        output_dir / "peak_route_network_edited.pdf",
        bbox_inches="tight",
    )
    fig.savefig(
        output_dir / "peak_route_network_edited.svg",
        bbox_inches="tight",
    )

    plt.close(fig)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate actual-road Peak scenario visualizations."
        )
    )
    parser.add_argument(
        "--graphml",
        type=Path,
        default=Path(
            "data/gunadarma_drive_network.graphml"
        ),
        help=(
            "Frozen GraphML road network used for visualization."
        ),
    )
    parser.add_argument(
        "--download-if-missing",
        action="store_true",
        help=(
            "Compatibility flag. The script now downloads and saves the "
            "OSM network automatically when GraphML is missing."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("figures"),
        help="Output directory. Default: figures.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    validate_routes()

    graph = load_or_download_graph(
        graphml_path=args.graphml,
        download_if_missing=args.download_if_missing,
    )
    snapped_nodes = nearest_graph_nodes(graph)

    trip_geometries: list[dict[str, Any]] = []

    for trip in PEAK_TRIPS:
        geometry = build_trip_geometry(
            graph,
            snapped_nodes,
            trip["route"],
        )

        trip_geometries.append(
            {
                **trip,
                "geometry_lon_lat": geometry,
            }
        )

    export_geojson(
        args.output_dir / "peak_route_geometry.geojson",
        trip_geometries,
    )
    create_interactive_map(
        args.output_dir / "peak_route_interactive.html",
        trip_geometries,
    )
    create_static_figure(
        args.output_dir,
        graph,
        trip_geometries,
    )

    print("=" * 72)
    print("Peak route visualization completed.")
    print("=" * 72)
    print(
        (
            args.output_dir
            / "peak_route_network_edited_600dpi.png"
        ).resolve()
    )
    print(
        (
            args.output_dir
            / "peak_route_network_edited.pdf"
        ).resolve()
    )
    print(
        (
            args.output_dir
            / "peak_route_network_edited.svg"
        ).resolve()
    )
    print(
        (
            args.output_dir
            / "peak_route_interactive.html"
        ).resolve()
    )
    print(
        (
            args.output_dir
            / "peak_route_geometry.geojson"
        ).resolve()
    )


if __name__ == "__main__":
    main()
