
"""RouteGrid core network engine.

Uses a weighted graph to represent a simulated Indian logistics network.
Distances and costs are illustrative, not live road or freight data.
"""

from __future__ import annotations

import networkx as nx


# City coordinates are approximate and used only for visualization.
CITY_DATA = {
    "Mumbai": {"state": "Maharashtra", "lat": 19.0760, "lon": 72.8777},
    "Pune": {"state": "Maharashtra", "lat": 18.5204, "lon": 73.8567},
    "Surat": {"state": "Gujarat", "lat": 21.1702, "lon": 72.8311},
    "Ahmedabad": {"state": "Gujarat", "lat": 23.0225, "lon": 72.5714},
    "Indore": {"state": "Madhya Pradesh", "lat": 22.7196, "lon": 75.8577},
    "Nagpur": {"state": "Maharashtra", "lat": 21.1458, "lon": 79.0882},
    "Hyderabad": {"state": "Telangana", "lat": 17.3850, "lon": 78.4867},
    "Bengaluru": {"state": "Karnataka", "lat": 12.9716, "lon": 77.5946},
    "Chennai": {"state": "Tamil Nadu", "lat": 13.0827, "lon": 80.2707},
    "Delhi": {"state": "Delhi", "lat": 28.6139, "lon": 77.2090},
    "Jaipur": {"state": "Rajasthan", "lat": 26.9124, "lon": 75.7873},
    "Lucknow": {"state": "Uttar Pradesh", "lat": 26.8467, "lon": 80.9462},
    "Bhopal": {"state": "Madhya Pradesh", "lat": 23.2599, "lon": 77.4126},
    "Kolkata": {"state": "West Bengal", "lat": 22.5726, "lon": 88.3639},
    "Visakhapatnam": {"state": "Andhra Pradesh", "lat": 17.6868, "lon": 83.2185},
}


# Each entry: (city A, city B, illustrative distance in km).
ROUTE_DATA = [
    ("Mumbai", "Pune", 150),
    ("Mumbai", "Surat", 280),
    ("Surat", "Ahmedabad", 265),
    ("Ahmedabad", "Jaipur", 660),
    ("Jaipur", "Delhi", 280),
    ("Delhi", "Lucknow", 550),
    ("Delhi", "Indore", 810),
    ("Indore", "Bhopal", 195),
    ("Bhopal", "Nagpur", 350),
    ("Pune", "Hyderabad", 560),
    ("Pune", "Bengaluru", 840),
    ("Hyderabad", "Nagpur", 500),
    ("Hyderabad", "Bengaluru", 570),
    ("Hyderabad", "Chennai", 630),
    ("Bengaluru", "Chennai", 350),
    ("Nagpur", "Kolkata", 1050),
    ("Delhi", "Kolkata", 1530),
    ("Lucknow", "Kolkata", 990),
    ("Chennai", "Visakhapatnam", 800),
    ("Visakhapatnam", "Kolkata", 880),
    ("Ahmedabad", "Indore", 390),
    ("Bhopal", "Hyderabad", 650),
    ("Nagpur", "Hyderabad", 500),
    ("Pune", "Indore", 590),
    ("Mumbai", "Bengaluru", 980),
]


def build_network() -> nx.Graph:
    """Build and return the default undirected logistics graph."""
    graph = nx.Graph()

    for city, details in CITY_DATA.items():
        graph.add_node(city, **details)

    for city_a, city_b, distance_km in ROUTE_DATA:
        graph.add_edge(
            city_a,
            city_b,
            distance_km=distance_km,
            travel_hours=distance_km / 45.0,
            cost_inr=distance_km * 18.0,
            available=True,
        )

    return graph


def get_available_graph(
    graph: nx.Graph,
    closed_roads: list[tuple[str, str]] | None = None,
) -> nx.Graph:
    """Return a copy with the selected roads removed."""
    available_graph = graph.copy()

    for city_a, city_b in closed_roads or []:
        if available_graph.has_edge(city_a, city_b):
            available_graph.remove_edge(city_a, city_b)

    return available_graph


def find_shortest_route(
    graph: nx.Graph,
    origin: str,
    destination: str,
    weight: str = "distance_km",
) -> dict:
    """Find a minimum-weight route and return its metrics.

    Supported weights: distance_km, travel_hours, cost_inr.
    """
    supported_weights = {"distance_km", "travel_hours", "cost_inr"}

    if weight not in supported_weights:
        raise ValueError(f"Unsupported route weight: {weight}")

    if origin not in graph:
        raise ValueError(f"Unknown origin: {origin}")

    if destination not in graph:
        raise ValueError(f"Unknown destination: {destination}")

    if origin == destination:
        return {
            "route": [origin],
            "distance_km": 0.0,
            "travel_hours": 0.0,
            "cost_inr": 0.0,
        }

    try:
        route = nx.shortest_path(graph, origin, destination, weight=weight)
    except nx.NetworkXNoPath:
        return {
            "route": [],
            "distance_km": None,
            "travel_hours": None,
            "cost_inr": None,
        }

    distance = 0.0
    travel_hours = 0.0
    cost = 0.0

    for city_a, city_b in zip(route, route[1:]):
        edge = graph[city_a][city_b]
        distance += edge["distance_km"]
        travel_hours += edge["travel_hours"]
        cost += edge["cost_inr"]

    return {
        "route": route,
        "distance_km": round(distance, 2),
        "travel_hours": round(travel_hours, 2),
        "cost_inr": round(cost, 2),
    }


def get_network_summary(graph: nx.Graph) -> dict:
    """Return basic connectivity and network statistics."""
    components = list(nx.connected_components(graph))

    return {
        "city_count": graph.number_of_nodes(),
        "road_count": graph.number_of_edges(),
        "component_count": len(components),
        "is_connected": nx.is_connected(graph),
        "components": [sorted(component) for component in components],
    }
