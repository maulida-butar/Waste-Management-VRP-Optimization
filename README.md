# Geospatial CVRP Optimization for Institutional Waste Collection Using Google OR-Tools and Directed Road-Network Distances

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Optimization: Google OR-Tools](https://img.shields.io/badge/Optimization-Google%20OR%20Tools-orange.svg)](https://developers.google.com/optimization)

This repository contains the complete reproducibility package for the research paper: **"Geospatial CVRP Optimization for Institutional Waste Collection Using Google OR-Tools and Directed Road-Network Distances"**. 

The study models the multi-campus institutional waste collection network of Universitas Gunadarma (comprising 1 central depot and 12 campus nodes) as a Capacitated Vehicle Routing Problem (CVRP) utilizing asymmetric directed road networks derived from OpenStreetMap via OSMnx.

---

## Repository Structure

```text
├── figures/
│   ├── Figure 1      # Research framework
│   ├── Figure 2      # Spatial distribution of waste collection nodes 
│   ├── Figure 3      # Geospatial visualization of the optimized under the Normal scenario
│   └── Figure 4      # Exact-optimal sequential route under the Peak-demand scenario
├── results/
│   ├── road_distance/                   # Directed distance matrices, snapping audits, and metadata
│   ├── gls_experiments/                 # 30-run repeatability summaries, run-level logs, and frequencies
│   ├── exact_validation/                # Held-Karp dynamic programming exact comparison files and summary
│   └── vrp_solver_results.json          # Core optimization solver output across scenarios
├── Road_Distance_revised.py             # OSMnx directed road-distance matrix generator and auditor
├── VRP_Solver_revised.py                # Core CVRP solver script using Google OR-Tools (Normal, Buffered, Peak)
├── exact_validation.py                  # Exact dynamic-programming optimization benchmark script (Held-Karp)
├── run_gls_experiments.py               # Script for executing 30 repeated GLS runs (stability & repeatability analysis)
└── Route_Visualization_Peak_revised.py  # Script for generating static and interactive map visualizations
