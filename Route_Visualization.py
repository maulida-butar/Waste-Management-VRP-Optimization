import folium
from folium.plugins import AntPath

# 1. Campus Coordinates (Gunadarma University Network)
# Mapping index to geographic location
locations = {
    0:  {"name": "Depot (Campus D)", "lat": -6.367957022267902, "lon": 106.83309635890863},
    1:  {"name": "Campus E", "lat": -6.353752172254033, "lon": 106.84159316305178},
    2:  {"name": "Campus G", "lat": -6.354234721369049, "lon": 106.84338356106764},
    3:  {"name": "Campus F4", "lat": -6.373649813990326, "lon": 106.86318582486531},
    4:  {"name": "Campus F5", "lat": -6.369296220683817, "lon": 106.83676819212762},
    5:  {"name": "Campus F6", "lat": -6.345757033149296, "lon": 106.85435354308778},
    6:  {"name": "Campus F7", "lat": -6.344363093455065, "lon": 106.88307686504615},
    7:  {"name": "Campus S (Simatupang)", "lat": -6.296769680410338, "lon": 106.82973599992759},
    8:  {"name": "Campus C (Salemba)", "lat": -6.196973702159097, "lon": 106.85209241771877},
    9:  {"name": "Campus J1", "lat": -6.248946372849019, "lon": 106.97054774544556},
    10: {"name": "Campus J3", "lat": -6.261687568292143, "lon": 107.02297516022837},
    11: {"name": "Campus J6", "lat": -6.258541893722087, "lon": 106.95892368892778},
    12: {"name": "Campus K (Tangerang)", "lat": -6.232345261132437, "lon": 106.61554334227392}
}

# 2. Optimized Route Sequence (Normal Scenario)
# Sequence: D -> F5 -> G -> E -> F6 -> F4 -> F7 -> J6 -> J1 -> J3 -> C -> S -> K -> D
optimized_sequence = [0, 4, 2, 1, 5, 3, 6, 11, 9, 10, 8, 7, 12, 0]

# 3. Initialize Map (Centered at Depot - Margonda)
m = folium.Map(
    location=[locations[0]["lat"], locations[0]["lon"]],
    zoom_start=11,
    tiles='CartoDB positron' # Clean white background for academic publication
)

# 4. Add Markers with Stop Numbers
for step, node_index in enumerate(optimized_sequence):
    data = locations[node_index]
    
    # Depot styling
    if node_index == 0:
        color = 'red'
        icon = 'home'
        label = "DEPOT"
    else:
        color = 'blue'
        icon = 'info-sign'
        label = f"Stop {step}"

    folium.Marker(
        location=[data["lat"], data["lon"]],
        popup=f"<b>{label}: {data['name']}</b>",
        tooltip=f"{label}: {data['name']}",
        icon=folium.Icon(color=color, icon=icon, prefix='glyphicon')
    ).add_to(m)

# 5. Draw Optimized Route Path using AntPath (Animated Effect)
route_coords = [[locations[i]["lat"], locations[i]["lon"]] for i in optimized_sequence]

AntPath(
    locations=route_coords,
    dash_array=[10, 20],
    delay=1000,
    color='green',
    pulse_color='white',
    weight=5,
    opacity=0.7
).add_to(m)

# 6. Save and Export
output_file = "VRP_Optimized_Route_Normal.html"
m.save(output_file)
print(f"Map successfully generated: {output_file}")

# Display for Jupyter/Colab
m
