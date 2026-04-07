"""
Project: Waste Management VRP Optimization - Universitas Gunadarma
Author: Maulida-butar
Description: Script to calculate the distance matrix using the Haversine formula.
Ref:
"""
__author__ = "Maulida-butar"

import pandas as pd
import numpy as np

# 1. Waste Collection Nodes at Universitas Gunadarma Based on Table 1
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

# 2. Haversine Function 
def haversine(lat1, lon1, lat2, lon2):
    """
    Calculates the Great-Circle distance using the Haversine formula.
    Used as a theoretical baseline for Circuity Factor analysis.
    Ref:
    """
    # Earth's radius in kilometers
    R = 6371.0
    
    # Convert degrees to radians
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    
    # Haversine formula
    a = np.sin(dphi / 2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    
    return R * c

# 3. Generate 13x13 Distance Matrix
names = [loc["name"] for loc in locations]
n = len(locations)
haversine_matrix = np.zeros((n, n))

for i in range(n):
    for j in range(n):
        haversine_matrix[i, j] = haversine(
            locations[i]["lat"], locations[i]["lon"],
            locations[j]["lat"], locations[j]["lon"]
        )

# 4. Display and Export Results
df_haversine = pd.DataFrame(haversine_matrix, index=names, columns=names)
print("Haversine Distance Matrix (KM):")
print(df_haversine.round(2))

# Export to CSV for comparative analysis in the Results section
df_haversine.to_csv("matrix_haversine_gunadarma.csv")
