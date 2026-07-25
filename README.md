# Geospatial CVRP Optimization for Institutional Waste Collection Using Google OR-Tools and Directed Road-Network Distances

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%252B-blue.svg)](https://www.python.org/)
[![Optimization: Google OR-Tools](https://img.shields.io/badge/Optimization-Google%20OR%20Tools-orange.svg)](https://developers.google.com/optimization)

This repository contains the complete reproducibility package for the research paper: **"Geospatial CVRP Optimization for Institutional Waste Collection Using Google OR-Tools and Directed Road-Network Distances"**. 

The study models the multi-campus institutional waste collection network of Universitas Gunadarma (comprising 1 central depot and 12 campus nodes) as a Capacitated Vehicle Routing Problem (CVRP) utilizing asymmetric directed road networks derived from OpenStreetMap via OSMnx.

---

## Repository Structure

```text
├── data/
│   └── gunadarma_drive_network.graphml  # Frozen OpenStreetMap driving network snapshot
├── figures/
│   ├── peak_route_interactive.html      # Interactive Map for the Peak (Multi-Trip) Scenario
│   └── normal_route_interactive.html    # Interactive Map for the Normal Scenario
├── results/
│   ├── road_distance/                   # Directed distance matrices and snapping audits
│   ├── gls_experiments/                 # 30-run repeatability summaries and run-level logs
│   └── exact_validation/                # Held-Karp dynamic programming exact comparison files
├── VRP_Solver_revised.py                # Core CVRP solver script using Google OR-Tools
├── Road_Distance_revised.py             # OSMnx directed road-distance matrix generator
├── exact_validation.py                  # Exact dynamic-programming optimization benchmark script
├── run_gls_experiments.py               # Script for executing 30 repeated GLS runs (stability analysis)
└── Route_Visualization_Peak_revised.py  # Script for generating static and interactive map visualizations
