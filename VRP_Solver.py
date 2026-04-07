"""
Project: Waste Management VRP Optimization - Universitas Gunadarma
File: VRP_Solver.py
Author: Maulida-butar
Description: 
    This script solves the Capacitated Vehicle Routing Problem (CVRP) 
    for Universitas Gunadarma waste collection using Google OR-Tools.
    It includes three operational scenarios: Normal, Buffered, and Peak.
"""

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

def create_data_model():
    """Stores all input data for the Google OR-Tools solver."""
    data = {}
    
    # 1. REAL-WORLD ROAD DISTANCE MATRIX (13x13 in KM)
    # Calculated via OSMnx in Road_Distance.py
    data['distance_matrix'] = [
        [ 0.0, 3.011, 2.957, 6.619, 3.511, 5.281, 9.690, 10.960, 21.758, 26.336, 31.588, 31.745, 39.655], 
        [ 3.484, 0.0, 0.125, 3.959, 2.977, 2.621, 7.030, 10.718, 20.838, 23.572, 28.825, 28.981, 39.121], 
        [ 3.430, 0.125, 0.0, 3.905, 2.923, 2.567, 6.976, 10.664, 20.810, 23.544, 28.796, 28.953, 39.067], 
        [ 6.333, 4.083, 4.028, 0.0, 6.691, 4.432, 5.668, 14.303, 22.410, 23.085, 28.217, 28.667, 39.323], 
        [ 2.075, 3.505, 3.450, 5.762, 0.0, 5.775, 10.184, 11.453, 22.252, 26.829, 32.081, 32.238, 36.670], 
        [ 5.745, 2.630, 2.576, 4.578, 5.238, 0.0, 5.042, 11.314, 19.420, 21.664, 26.704, 26.861, 41.245], 
        [ 10.150, 7.035, 6.981, 5.293, 9.643, 5.175, 0.0, 12.096, 19.988, 17.801, 22.842, 23.000, 42.028], 
        [ 10.887, 9.937, 9.883, 12.871, 10.380, 10.053, 11.090, 0.0, 14.595, 20.993, 26.247, 26.404, 34.535], 
        [ 21.123, 20.173, 20.118, 21.987, 20.616, 19.254, 19.096, 13.765, 0.0, 16.698, 22.404, 24.225, 31.540], 
        [ 26.192, 22.965, 22.936, 22.536, 25.685, 21.493, 17.631, 21.027, 17.586, 0.0, 7.935, 8.092, 45.359], 
        [ 31.767, 28.540, 28.512, 27.922, 31.260, 26.490, 22.629, 27.392, 23.952, 6.874, 0.0, 8.034, 51.724], 
        [ 28.082, 24.855, 24.826, 24.425, 27.575, 23.382, 19.521, 22.917, 18.208, 4.298, 10.724, 0.0, 47.250], 
        [ 37.374, 39.145, 39.090, 40.026, 39.587, 41.415, 43.150, 32.397, 30.925, 46.112, 52.538, 53.849, 0.0]  
    ]

    # 2. SELECT OPERATIONAL SCENARIO
    # Options: "normal", "buffered", or "peak"
    scenario = "normal" 

    if scenario == "normal":
        data['demands'] = [0, 10, 8, 14, 12, 9, 11, 13, 16, 10, 8, 9, 6] # Total: 126
        data['num_vehicles'] = 1
    elif scenario == "buffered":
        data['demands'] = [0, 12, 10, 17, 14, 11, 13, 16, 19, 12, 10, 11, 7] # Total: 152
        data['num_vehicles'] = 1
    elif scenario == "peak":
        data['demands'] = [0, 15, 12, 20, 18, 14, 16, 20, 24, 15, 13, 14, 10] # Total: 191
        data['num_vehicles'] = 2 # Multi-trip required as 191 > 180 capacity

    data['vehicle_capacities'] = [180] * data['num_vehicles']
    data['depot'] = 0 
    return data

def print_solution(data, manager, routing, solution):
    """Prints the optimized route sequence and performance summary."""
    print(f"Solving for Scenario: {data.get('scenario_name', 'Default')}")
    print("=========================================================")
    print(f"Total Combined Distance: {solution.ObjectiveValue() / 1000:.2f} km")
    print("=========================================================\n")
    
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        plan_output = f"Route for Vehicle {vehicle_id + 1}:\n"
        route_distance = 0
        route_load = 0
        
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            route_load += data['demands'][node_index]
            plan_output += f" Campus {node_index} (Load: {route_load}) -> "
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
            
        node_index = manager.IndexToNode(index)
        plan_output += f" Depot {node_index} (End)\n\n"
        plan_output += f"Route Distance: {route_distance / 1000:.2f} km\n"
        plan_output += f"Total Load Carried: {route_load} boxes\n"
        print(plan_output)

def main():
    """Main CVRP entry point."""
    data = create_data_model()

    manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']),
                                           data['num_vehicles'], data['depot'])
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(data['distance_matrix'][from_node][to_node] * 1000)

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return data['demands'][from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index, 0, data['vehicle_capacities'], True, 'Capacity')

    # Search Parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    search_parameters.time_limit.FromSeconds(10)

    solution = routing.SolveWithParameters(search_parameters)
    if solution:
        print_solution(data, manager, routing, solution)
    else:
        print("No feasible route found.")

if __name__ == '__main__':
    main()
