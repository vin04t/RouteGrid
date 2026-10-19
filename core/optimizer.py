
"""RouteGrid multi-stop delivery optimization."""

from __future__ import annotations

from itertools import permutations

import networkx as nx

from core.network import find_shortest_route


def build_distance_matrix(
    graph: nx.Graph,
    locations: list[str],
    weight: str = "distance_km",
) -> dict[tuple[str, str], float]:
    """Calculate shortest-path costs between all selected locations."""
    matrix = {}

    for source in locations:
        for destination in locations:
            if source == destination:
                matrix[(source, destination)] = 0.0
                continue

            result = find_shortest_route(
                graph, source, destination, weight=weight
            )
            value = result[weight]
            # Represent unreachable pairs as infinity so route-cost
            # calculations can reject them without raising TypeError.
            matrix[(source, destination)] = (
                float("inf") if value is None else float(value)
            )

    return matrix


def calculate_tour_cost(
    stops: list[str],
    matrix: dict[tuple[str, str], float],
    return_to_depot: bool = True,
) -> float:
    """Calculate the total cost of visiting stops in the given order."""
    if len(stops) < 2:
        return 0.0

    total = 0.0

    for source, destination in zip(stops, stops[1:]):
        cost = matrix.get((source, destination))
        if cost is None:
            return float("inf")
        total += cost

    if return_to_depot:
        return_cost = matrix.get((stops[-1], stops[0]))
        if return_cost is None:
            return float("inf")
        total += return_cost

    return total


def optimize_delivery_order(
    graph: nx.Graph,
    depot: str,
    destinations: list[str],
    weight: str = "distance_km",
    return_to_depot: bool = True,
    exact_search_limit: int = 8,
) -> dict:
    """Find a good delivery order.

    Uses exhaustive permutation search for small batches and a
    nearest-neighbor heuristic for larger batches.

    The depot is the starting point. If return_to_depot is True,
    the truck must return to the depot after its final delivery.
    """
    if depot not in graph:
        raise ValueError(f"Unknown depot: {depot}")

    if weight not in {"distance_km", "travel_hours", "cost_inr"}:
        raise ValueError(f"Unsupported optimization weight: {weight}")

    if len(destinations) != len(set(destinations)):
        raise ValueError("Each delivery destination must be unique.")

    if depot in destinations:
        raise ValueError("The depot must not also be a delivery destination.")

    unknown = [city for city in destinations if city not in graph]
    if unknown:
        raise ValueError(f"Unknown destination(s): {', '.join(unknown)}")

    if not destinations:
        return {
            "route": [depot],
            "objective_value": 0.0,
            "method": "No deliveries",
            "legs": [],
            "feasible": True,
        }

    locations = [depot, *destinations]
    matrix = build_distance_matrix(graph, locations, weight)

    def leg_cost(source: str, destination: str) -> float:
        return matrix.get((source, destination), float("inf"))

    def route_cost(route: list[str]) -> float:
        cost = sum(
            leg_cost(a, b) for a, b in zip(route, route[1:])
        )
        if return_to_depot:
            cost += leg_cost(route[-1], depot)
        return cost

    if len(destinations) <= exact_search_limit:
        best_route = None
        best_cost = float("inf")

        for ordering in permutations(destinations):
            candidate = [depot, *ordering]
            cost = route_cost(candidate)

            if cost < best_cost:
                best_route = candidate
                best_cost = cost

        method = "Exact permutation search"
    else:
        remaining = set(destinations)
        current = depot
        best_route = [depot]

        while remaining:
            candidates = [
                (leg_cost(current, city), city)
                for city in remaining
            ]
            cost, next_city = min(candidates)

            if cost == float("inf"):
                return {
                    "route": [],
                    "objective_value": None,
                    "method": "Nearest-neighbor heuristic",
                    "legs": [],
                    "feasible": False,
                    "message": f"No route from {current} to any remaining stop.",
                }

            best_route.append(next_city)
            remaining.remove(next_city)
            current = next_city

        best_cost = route_cost(best_route)
        method = "Nearest-neighbor heuristic"

    if best_route is None or best_cost == float("inf"):
        return {
            "route": [],
            "objective_value": None,
            "method": method,
            "legs": [],
            "feasible": False,
            "message": "No feasible route visits every destination.",
        }

    complete_route = list(best_route)
    if return_to_depot:
        complete_route.append(depot)

    legs = []
    for source, destination in zip(complete_route, complete_route[1:]):
        path_result = find_shortest_route(
            graph, source, destination, weight=weight
        )

        if not path_result["route"]:
            return {
                "route": [],
                "objective_value": None,
                "method": method,
                "legs": [],
                "feasible": False,
                "message": f"No available path from {source} to {destination}.",
            }

        legs.append({
            "from": source,
            "to": destination,
            "path": path_result["route"],
            "distance_km": path_result["distance_km"],
            "travel_hours": path_result["travel_hours"],
            "cost_inr": path_result["cost_inr"],
        })

    return {
        "route": complete_route,
        "objective_value": round(best_cost, 2),
        "method": method,
        "legs": legs,
        "feasible": True,
        "return_to_depot": return_to_depot,
    }
