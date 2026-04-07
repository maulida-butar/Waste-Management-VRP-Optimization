import folium
from folium.plugins import AntPath

# 1. Campus Coordinates
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

# 2. Optimized Sequences from OR-Tools (Peak Scenario)
route_1_seq = [0, 4, 0] # Short trip to F5
route_2_seq = [0, 2, 1, 5, 3, 6, 9, 10, 11, 8, 12, 7, 0] # Main loop

# 3. Initialize Map
m_peak = folium.Map(
    location=[locations[0]["lat"], locations[0]["lon"]],
    zoom_start=10,
    tiles='CartoDB positron'
)

# 4. Add Markers
for idx, data in locations.items():
    color = 'red' if idx == 0 else 'gray'
    icon = 'home' if idx == 0 else 'info-sign'
    
    folium.Marker(
        location=[data["lat"], data["lon"]],
        popup=f"<b>{data['name']}</b>",
        tooltip=data['name'],
        icon=folium.Icon(color=color, icon=icon)
    ).add_to(m_peak)

# 5. Draw Route 1 (Shuttle Trip - Orange)
coords_1 = [[locations[i]["lat"], locations[i]["lon"]] for i in route_1_seq]
AntPath(
    locations=coords_1,
    dash_array=[5, 15],
    delay=1500,
    color='orange',
    pulse_color='black',
    weight=6,
    opacity=0.9,
    tooltip="Route 1 (Shuttle)"
).add_to(m_peak)

# 6. Draw Route 2 (Main Loop - Purple)
coords_2 = [[locations[i]["lat"], locations[i]["lon"]] for i in route_2_seq]
AntPath(
    locations=coords_2,
    dash_array=[10, 20],
    delay=800,
    color='purple',
    pulse_color='white',
    weight=4,
    opacity=0.7,
    tooltip="Route 2 (Main Loop)"
).add_to(m_peak)

# 7. Add Legend (Using HTML)
legend_html = '''
     <div style="position: fixed; 
     bottom: 50px; left: 50px; width: 160px; height: 90px; 
     border:2px solid grey; z-index:9999; font-size:14px;
     background-color:white; opacity: 0.8; padding: 10px;">
     <b>Peak Scenario</b><br>
     <i style="background:orange; width:10px; height:10px; display:inline-block;"></i> Route 1 (5.59 km)<br>
     <i style="background:purple; width:10px; height:10px; display:inline-block;"></i> Route 2 (142.75 km)
     </div>
     '''
m_peak.get_root().html.add_child(folium.Element(legend_html))

# 8. Save
m_peak.save("VRP_Peak_Visualization.html")
print("Peak Visualization Map Generated!")
m_peak
