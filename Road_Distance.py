"""
Road Network Distance Matrix Generation
Author: Maulida-butar
Project: Waste Management VRP Optimization - Universitas Gunadarma
Description: Downloads OpenStreetMap (OSM) data and calculates a 13x13 
             real-world road distance matrix using OSMnx and NetworkX.
"""

import osmnx as ox
import networkx as nx
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# 1. Configuration
ox.settings.use_cache = True
ox.settings.timeout = 300 # Increase timeout for large urban areas

# 2. Campus Locations (13 Nodes)
locations = [
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
    {"name": "K", "lat": -6.232345261132437, "lon": 106.61554334227392}
 ]

# 3. Calculate Bounding Box (Bbox)
lats = [l["lat"] for l in locations]
lons = [l["lon"] for l in locations]
# OSMNX 2.0 format: (west, south, east, north)
padding = 0.03 # Approx 3km padding to avoid route clipping
w, s, e, n = min(lons)-padding, min(lats)-padding, max(lons)+padding, max(lats)+padding

# 4. Download and Project Street Network
print("Downloading street network for Gunadarma area...")
try:
    # Fetch driving network from the calculated bounding box
    graph_raw = ox.graph_from_bbox(bbox=(w, s, e, n), network_type="drive")
    # Project the graph to UTM (meters) for accurate length measurement
    graph = ox.project_graph(graph_raw)
    print("Graph downloaded and projected to UTM (meters) successfully.")
except Exception as err:
    print(f"Failed to download map: {err}")
    exit()

# 5. Prepare Campus Points (UTM Projection)
gdf = gpd.GeoDataFrame(locations, 
                       geometry=[Point(l['lon'], l['lat']) for l in locations], 
                       crs="EPSG:4326")
gdf_proj = gdf.to_crs(graph.graph['crs'])

# 6. Shortest Path Calculation (Road Network)
def get_road_dist(g, orig, dest):
    """
    Calculates the shortest road distance between two points.
    Returns distance in kilometers.
    """
    try:
        # Find the nearest network nodes to the campus coordinates
        node_u = ox.distance.nearest_nodes(g, orig.x, orig.y)
        node_v = ox.distance.nearest_nodes(g, dest.x, dest.y)
        
        if node_u == node_v: 
            return 0.2  # Minimum distance for adjacent campuses
            
        # Calculate the shortest path length based on street segments
        distance_meters = nx.shortest_path_length(g, node_u, node_v, weight='length')
        return distance_meters / 1000
    except Exception:
        return 999.0  # Penalty for unreachable routes in CVRP

# 7. Generate Distance Matrix
names = [l["name"] for l in locations]
size = len(names)
road_matrix = [[0.0]*size for _ in range(size)]

print("Calculating 13x13 road distance matrix...")
for i in range(size):
    for j in range(size):
        if i != j:
            road_matrix[i][j] = get_road_dist(graph, gdf_proj.iloc[i].geometry, gdf_proj.iloc[j].geometry)

# 8. Export and Display Results
df_road = pd.DataFrame(road_matrix, index=names, columns=names)
df_road.to_csv("matrix_road_gunadarma.csv")

print("\nRoad Network Matrix complete and saved to 'matrix_road_gunadarma.csv'!")
print(df_road.round(2))
