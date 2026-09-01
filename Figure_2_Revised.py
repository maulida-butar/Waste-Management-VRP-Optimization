"""Create a publication-ready spatial distribution figure
Geospatial CVRP Optimization for Institutional Waste Collection Using Google OR-Tools and Directed Road-Network Distances
Journal Environmental Management: Smart Solutions
Maulida Boru Butar Butar

The figure contains:
    (a) a regional overview of all 13 study nodes; and
    (b) an enlarged inset of the seven-node Depok cluster.

The script intentionally uses only the manuscript coordinates rather than a
live web basemap. This keeps the figure reproducible, avoids browser controls,
and prevents labels from changing when map tiles are updated.

Outputs (written to --output-dir):
    Figure_2_revised.png  - opaque, high-resolution raster
    Figure_2_revised.pdf  - vector figure preferred for submission
    Figure_2_revised.svg  - editable vector figure

Example:
    python Figure_2_revised.py --output-dir figures --dpi 600
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from PIL import Image


NODES = [
    {"code": "D", "name": "Campus D (Depot)", "lat": -6.367957022267902, "lon": 106.83309635890863, "region": "Depok", "depot": True},
    {"code": "E", "name": "Campus E", "lat": -6.353752172254033, "lon": 106.84159316305178, "region": "Depok", "depot": False},
    {"code": "G", "name": "Campus G", "lat": -6.354234721369049, "lon": 106.84338356106764, "region": "Depok", "depot": False},
    {"code": "F4", "name": "Campus F4", "lat": -6.373649813990326, "lon": 106.86318582486531, "region": "Depok", "depot": False},
    {"code": "F5", "name": "Campus F5", "lat": -6.369296220683817, "lon": 106.83676819212762, "region": "Depok", "depot": False},
    {"code": "F6", "name": "Campus F6", "lat": -6.345757033149296, "lon": 106.85435354308778, "region": "Depok", "depot": False},
    {"code": "F7", "name": "Campus F7", "lat": -6.344363093455065, "lon": 106.88307686504615, "region": "Depok", "depot": False},
    {"code": "S", "name": "Campus S (Simatupang)", "lat": -6.296769680410338, "lon": 106.82973599992759, "region": "South Jakarta", "depot": False},
    {"code": "C", "name": "Campus C", "lat": -6.196973702159097, "lon": 106.85209241771877, "region": "Central Jakarta", "depot": False},
    {"code": "J1", "name": "Campus J1", "lat": -6.248946372849019, "lon": 106.97054774544556, "region": "Bekasi", "depot": False},
    {"code": "J3", "name": "Campus J3", "lat": -6.261687568292143, "lon": 107.02297516022837, "region": "Bekasi", "depot": False},
    {"code": "J6", "name": "Campus J6", "lat": -6.258541893722087, "lon": 106.95892368892778, "region": "Bekasi", "depot": False},
    {"code": "K", "name": "Campus K", "lat": -6.232345261132437, "lon": 106.61554334227392, "region": "Tangerang", "depot": False},
]


DEPOT_COLOR = "#b2182b"
NODE_COLOR = "#2166ac"
EDGE_COLOR = "#172f55"
GRID_COLOR = "#d8dde6"
BACKGROUND_COLOR = "#f7f8fa"

DEPOK_CODES = {"D", "E", "G", "F4", "F5", "F6", "F7"}

# Label positions are set manually to prevent collision at publication size.
REGIONAL_LABEL_OFFSETS = {
    "K": (7, 7),
    "S": (7, 7),
    "C": (7, 7),
    "J1": (7, 8),
    "J3": (7, -3),
    "J6": (-30, -13),
}

DEPOK_LABEL_OFFSETS = {
    "D": (-20, 9),
    "E": (-26, 12),
    "G": (10, -12),
    "F4": (8, -9),
    "F5": (-22, -15),
    "F6": (7, 10),
    "F7": (7, 8),
}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the revised two-panel Figure 2."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("figures"),
        help="Output directory (default: figures).",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=600,
        help="PNG resolution in dots per inch (default: 600).",
    )
    return parser.parse_args()


def configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9.8,
            "axes.titlesize": 11.5,
            "axes.labelsize": 10.0,
            "xtick.labelsize": 9.0,
            "ytick.labelsize": 9.0,
            "axes.edgecolor": EDGE_COLOR,
            "axes.linewidth": 0.8,
            "savefig.facecolor": "white",
            "savefig.transparent": False,
        }
    )


def node_by_code(code: str) -> dict[str, object]:
    for node in NODES:
        if node["code"] == code:
            return node
    raise KeyError(code)


def plot_marker(ax: plt.Axes, node: dict[str, object], size: float) -> None:
    is_depot = bool(node["depot"])
    ax.scatter(
        float(node["lon"]),
        float(node["lat"]),
        s=size * (1.20 if is_depot else 1.0),
        marker="s" if is_depot else "o",
        facecolor=DEPOT_COLOR if is_depot else NODE_COLOR,
        edgecolor="white",
        linewidth=0.9,
        zorder=5,
    )


def annotate_node(
    ax: plt.Axes,
    node: dict[str, object],
    offset: tuple[float, float],
    fontsize: float = 9.4,
) -> None:
    ax.annotate(
        str(node["code"]),
        xy=(float(node["lon"]), float(node["lat"])),
        xytext=offset,
        textcoords="offset points",
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight="bold",
        color="#111111",
        arrowprops={
            "arrowstyle": "-",
            "color": "#606b7a",
            "linewidth": 0.65,
            "shrinkA": 1,
            "shrinkB": 3,
        },
        bbox={
            "boxstyle": "round,pad=0.18",
            "facecolor": "white",
            "edgecolor": "#c7ccd4",
            "linewidth": 0.45,
            "alpha": 0.96,
        },
        zorder=7,
    )


def set_geographic_aspect(ax: plt.Axes, reference_latitude: float) -> None:
    # Correct the small east-west scale distortion in longitude/latitude axes.
    ax.set_aspect(1.0 / math.cos(math.radians(reference_latitude)))
    ax.set_anchor("N")


def style_axes(ax: plt.Axes) -> None:
    ax.set_facecolor(BACKGROUND_COLOR)
    ax.grid(
        True,
        color=GRID_COLOR,
        linewidth=0.55,
        linestyle=(0, (2, 3)),
        zorder=0,
    )
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°S)")
    ax.ticklabel_format(style="plain", useOffset=False)


def add_north_arrow(ax: plt.Axes) -> None:
    ax.annotate(
        "N",
        xy=(0.955, 0.92),
        xytext=(0.955, 0.79),
        xycoords="axes fraction",
        textcoords="axes fraction",
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
        arrowprops={
            "arrowstyle": "-|>",
            "color": "#111111",
            "linewidth": 1.1,
        },
        zorder=9,
    )


def add_scale_bar(
    ax: plt.Axes,
    length_km: float,
    y_fraction: float = 0.07,
) -> None:
    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()
    mean_lat = (y_min + y_max) / 2.0
    km_per_degree_lon = 111.32 * math.cos(math.radians(mean_lat))
    length_degrees = length_km / km_per_degree_lon

    x_start = x_min + 0.06 * (x_max - x_min)
    y = y_min + y_fraction * (y_max - y_min)
    x_end = x_start + length_degrees

    ax.plot(
        [x_start, x_end],
        [y, y],
        color="#111111",
        linewidth=2.0,
        solid_capstyle="butt",
        zorder=9,
    )
    tick_height = 0.012 * (y_max - y_min)
    ax.plot([x_start, x_start], [y - tick_height, y + tick_height], color="#111111", linewidth=1.0, zorder=9)
    ax.plot([x_end, x_end], [y - tick_height, y + tick_height], color="#111111", linewidth=1.0, zorder=9)
    ax.text(
        (x_start + x_end) / 2.0,
        y + 0.018 * (y_max - y_min),
        f"{length_km:g} km",
        ha="center",
        va="bottom",
        fontsize=8.5,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 1.0},
        zorder=10,
    )


def add_region_labels(ax: plt.Axes) -> None:
    region_positions = {
        "TANGERANG": (106.665, -6.185),
        "JAKARTA": (106.800, -6.170),
        "BEKASI": (107.000, -6.205),
        "DEPOK": (106.785, -6.402),
    }
    for label, (lon, lat) in region_positions.items():
        ax.text(
            lon,
            lat,
            label,
            color="#a5adb9",
            fontsize=7.8,
            fontweight="bold",
            ha="center",
            va="center",
            zorder=1,
        )


def draw_regional_panel(ax: plt.Axes) -> None:
    style_axes(ax)
    ax.set_title("(a) Regional overview", loc="left", fontweight="bold", pad=7)
    ax.set_xlim(106.57, 107.07)
    ax.set_ylim(-6.415, -6.155)
    set_geographic_aspect(ax, -6.285)
    add_region_labels(ax)

    for node in NODES:
        plot_marker(ax, node, size=38)
        code = str(node["code"])
        if code in REGIONAL_LABEL_OFFSETS:
            annotate_node(ax, node, REGIONAL_LABEL_OFFSETS[code], fontsize=9.2)

    # Identify the enlarged area without repeating the crowded node labels.
    depok_rect = Rectangle(
        (106.826, -6.381),
        106.889 - 106.826,
        -6.338 - (-6.381),
        fill=False,
        edgecolor="#58677d",
        linewidth=1.0,
        linestyle=(0, (4, 3)),
        zorder=6,
    )
    ax.add_patch(depok_rect)
    ax.annotate(
        "Depok cluster\n(7 nodes; see panel b)",
        xy=(106.858, -6.358),
        xytext=(-72, 34),
        textcoords="offset points",
        ha="right",
        va="bottom",
        fontsize=8.5,
        color="#34445a",
        arrowprops={"arrowstyle": "->", "color": "#58677d", "linewidth": 0.8},
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#c7ccd4", "linewidth": 0.5},
        zorder=8,
    )

    add_north_arrow(ax)
    add_scale_bar(ax, length_km=10)

    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="s",
            color="none",
            markerfacecolor=DEPOT_COLOR,
            markeredgecolor="white",
            markeredgewidth=0.8,
            markersize=7.5,
            label="Depot (Campus D)",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=NODE_COLOR,
            markeredgecolor="white",
            markeredgewidth=0.8,
            markersize=7.0,
            label="Collection node",
        ),
    ]
    ax.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=2,
        frameon=True,
        framealpha=0.97,
        facecolor="white",
        edgecolor="#c7ccd4",
        fontsize=8.5,
        borderpad=0.6,
    )


def draw_depok_panel(ax: plt.Axes) -> None:
    style_axes(ax)
    ax.set_title("(b) Depok cluster", loc="left", fontweight="bold", pad=7)
    ax.set_xlim(106.826, 106.889)
    ax.set_ylim(-6.381, -6.338)
    set_geographic_aspect(ax, -6.36)

    for code in ["D", "E", "G", "F4", "F5", "F6", "F7"]:
        node = node_by_code(code)
        plot_marker(ax, node, size=55)
        annotate_node(ax, node, DEPOK_LABEL_OFFSETS[code], fontsize=9.4)

    add_scale_bar(ax, length_km=2, y_fraction=0.085)


def save_outputs(
    fig: plt.Figure,
    output_dir: Path,
    dpi: int,
) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    png_path = output_dir / "Figure_2_revised.png"
    pdf_path = output_dir / "Figure_2_revised.pdf"
    svg_path = output_dir / "Figure_2_revised.svg"

    save_options = {
        "bbox_inches": "tight",
        "pad_inches": 0.06,
        "facecolor": "white",
        "transparent": False,
    }
    fig.savefig(png_path, dpi=dpi, **save_options)
    fig.savefig(pdf_path, **save_options)
    fig.savefig(svg_path, **save_options)

    # Matplotlib may encode an opaque alpha channel. Flatten explicitly so the
    # final PNG is true RGB with no transparency and carries correct DPI data.
    with Image.open(png_path) as image:
        rgba_image = image.convert("RGBA").copy()

    rgb_image = Image.new("RGB", rgba_image.size, "white")
    rgb_image.paste(rgba_image, mask=rgba_image.getchannel("A"))
    temporary_png_path = png_path.with_name(f"{png_path.stem}.rgb.png")
    rgb_image.save(
        temporary_png_path,
        dpi=(dpi, dpi),
        optimize=True,
    )
    temporary_png_path.replace(png_path)

    return png_path, pdf_path, svg_path


def main() -> None:
    args = parse_arguments()
    if args.dpi < 300:
        raise ValueError("Use at least 300 dpi for publication output.")

    configure_style()

    # The wider authoring canvas leaves room for the overview and inset. At a
    # 15.9 cm manuscript width, labels remain approximately 7.5-9 pt.
    fig = plt.figure(figsize=(8.0, 3.75), facecolor="white")
    grid = fig.add_gridspec(
        1,
        2,
        width_ratios=(2.05, 1.05),
        left=0.065,
        right=0.988,
        bottom=0.24,
        top=0.92,
        wspace=0.25,
    )
    regional_ax = fig.add_subplot(grid[0, 0])
    depok_ax = fig.add_subplot(grid[0, 1])

    draw_regional_panel(regional_ax)
    draw_depok_panel(depok_ax)

    fig.text(
        0.065,
        0.025,
        "Location coordinates correspond to Table 2; visualization generated by the authors.",
        ha="left",
        va="bottom",
        fontsize=8.3,
        color="#3f4854",
    )

    paths = save_outputs(fig, args.output_dir, args.dpi)
    plt.close(fig)

    print("Revised Figure 2 generated:")
    for path in paths:
        print(f"  {path.resolve()}")


if __name__ == "__main__":
    main()
