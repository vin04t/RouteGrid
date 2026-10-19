
"""RouteGrid order validation and balanced, route-aware allocation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import networkx as nx

from core.optimizer import optimize_delivery_order


@dataclass(frozen=True)
class DeliveryOrder:
    order_id: str
    destination: str
    quantity_kg: float
    deadline_hours: float | None = None


@dataclass(frozen=True)
class Vehicle:
    vehicle_id: str
    capacity_kg: float
    cost_per_km: float = 18.0


def validate_orders(orders: Iterable[DeliveryOrder]) -> list[str]:
    orders = list(orders)
    errors = []
    seen_ids = set()

    for order in orders:
        order_id = order.order_id.strip()

        if not order_id:
            errors.append("An order has an empty order ID.")
        elif order_id in seen_ids:
            errors.append(f"Duplicate order ID: {order_id}")
        seen_ids.add(order_id)

        if not order.destination.strip():
            errors.append(f"{order.order_id}: destination is required.")
        if order.quantity_kg <= 0:
            errors.append(
                f"{order.order_id}: quantity must be greater than zero."
            )
        if (
            order.deadline_hours is not None
            and order.deadline_hours <= 0
        ):
            errors.append(
                f"{order.order_id}: deadline must be greater than zero."
            )

    return errors


def validate_vehicle(vehicle: Vehicle) -> list[str]:
    errors = []

    if not vehicle.vehicle_id.strip():
        errors.append("Vehicle ID is required.")
    if vehicle.capacity_kg <= 0:
        errors.append("Vehicle capacity must be greater than zero.")
    if vehicle.cost_per_km < 0:
        errors.append("Cost per kilometre cannot be negative.")

    return errors


def allocate_orders_to_vehicle(
    orders: Iterable[DeliveryOrder],
    vehicle: Vehicle,
) -> dict:
    """Check whether all supplied orders fit in one vehicle."""
    orders = list(orders)
    errors = validate_orders(orders) + validate_vehicle(vehicle)

    if errors:
        return {
            "feasible": False,
            "errors": errors,
            "total_weight_kg": None,
            "remaining_capacity_kg": None,
            "utilization_percent": None,
        }

    total_weight = sum(order.quantity_kg for order in orders)
    remaining = vehicle.capacity_kg - total_weight
    feasible = total_weight <= vehicle.capacity_kg

    return {
        "feasible": feasible,
        "errors": [] if feasible else [
            "Total order weight exceeds vehicle capacity."
        ],
        "total_weight_kg": round(total_weight, 2),
        "remaining_capacity_kg": round(remaining, 2),
        "utilization_percent": round(
            total_weight / vehicle.capacity_kg * 100, 2
        ),
    }


def allocate_orders_greedily(
    orders: Iterable[DeliveryOrder],
    vehicles: Iterable[Vehicle],
) -> dict:
    """Basic first-fit allocation retained for comparison."""
    orders = list(orders)
    vehicles = list(vehicles)

    errors = validate_orders(orders)
    for vehicle in vehicles:
        errors.extend(validate_vehicle(vehicle))

    if len({v.vehicle_id for v in vehicles}) != len(vehicles):
        errors.append("Vehicle IDs must be unique.")

    if errors:
        return {
            "feasible": False,
            "errors": errors,
            "assignments": {},
            "unassigned_orders": [order.order_id for order in orders],
        }

    remaining = {v.vehicle_id: v.capacity_kg for v in vehicles}
    assignments = {v.vehicle_id: [] for v in vehicles}
    unassigned = []

    for order in sorted(orders, key=lambda item: item.quantity_kg, reverse=True):
        selected = next(
            (
                vehicle for vehicle in vehicles
                if remaining[vehicle.vehicle_id] >= order.quantity_kg
            ),
            None,
        )

        if selected is None:
            unassigned.append(order.order_id)
        else:
            assignments[selected.vehicle_id].append(order.order_id)
            remaining[selected.vehicle_id] -= order.quantity_kg

    return {
        "feasible": not unassigned,
        "errors": [] if not unassigned else [
            "Some orders could not be assigned within available capacities."
        ],
        "assignments": assignments,
        "remaining_capacity_kg": {
            key: round(value, 2) for key, value in remaining.items()
        },
        "unassigned_orders": unassigned,
    }


def allocate_orders_route_aware(
    orders: Iterable[DeliveryOrder],
    vehicles: Iterable[Vehicle],
    graph: nx.Graph,
    depot: str,
    return_to_depot: bool = True,
    balance_weight: float = 1200.0,
    reuse_penalty: float = 250.0,
) -> dict:
    """Allocate orders by incremental route distance and load balance.

    Orders are considered from heaviest to lightest. Candidate assignments
    are scored using:
      1. Additional estimated route distance.
      2. A penalty for projected vehicle-capacity utilization.
      3. A small penalty for adding another order to an already-used vehicle.

    This is a heuristic, not a globally optimal fleet solver.
    """
    orders = list(orders)
    vehicles = list(vehicles)

    errors = validate_orders(orders)
    for vehicle in vehicles:
        errors.extend(validate_vehicle(vehicle))

    if len({v.vehicle_id for v in vehicles}) != len(vehicles):
        errors.append("Vehicle IDs must be unique.")

    if depot not in graph:
        errors.append(f"Unknown depot: {depot}")

    if balance_weight < 0 or reuse_penalty < 0:
        errors.append("Balancing and reuse penalties cannot be negative.")

    for order in orders:
        if order.destination not in graph:
            errors.append(
                f"{order.order_id}: unknown destination "
                f"'{order.destination}'."
            )
        elif order.destination == depot:
            errors.append(
                f"{order.order_id}: destination cannot equal the depot."
            )

    if errors:
        return {
            "feasible": False,
            "errors": errors,
            "assignments": {},
            "unassigned_orders": [order.order_id for order in orders],
            "vehicle_routes": {},
        }

    assigned = {v.vehicle_id: [] for v in vehicles}
    remaining = {v.vehicle_id: v.capacity_kg for v in vehicles}

    def get_route(candidate_orders: list[DeliveryOrder]) -> dict:
        destinations = list(dict.fromkeys(
            order.destination for order in candidate_orders
        ))

        return optimize_delivery_order(
            graph,
            depot=depot,
            destinations=destinations,
            weight="distance_km",
            return_to_depot=return_to_depot,
        )

    def route_distance(candidate_orders: list[DeliveryOrder]) -> float:
        if not candidate_orders:
            return 0.0

        route_result = get_route(candidate_orders)
        if not route_result["feasible"]:
            return float("inf")

        return float(route_result["objective_value"])

    unassigned = []

    # Largest orders are handled first to reduce capacity failures.
    for order in sorted(orders, key=lambda item: item.quantity_kg, reverse=True):
        best_vehicle = None
        best_score = float("inf")

        for vehicle in vehicles:
            vehicle_id = vehicle.vehicle_id

            if remaining[vehicle_id] < order.quantity_kg:
                continue

            existing_orders = assigned[vehicle_id]
            old_distance = route_distance(existing_orders)
            proposed_orders = existing_orders + [order]
            new_distance = route_distance(proposed_orders)

            if new_distance == float("inf"):
                continue

            added_distance = max(0.0, new_distance - old_distance)
            projected_load = (
                vehicle.capacity_kg - remaining[vehicle_id] + order.quantity_kg
            )
            projected_utilization = projected_load / vehicle.capacity_kg

            # The penalties make load balance part of the decision.
            balance_penalty = balance_weight * projected_utilization**2
            reuse_cost = reuse_penalty if existing_orders else 0.0

            score = added_distance + balance_penalty + reuse_cost

            if score < best_score:
                best_score = score
                best_vehicle = vehicle

        if best_vehicle is None:
            unassigned.append(order.order_id)
            continue

        vehicle_id = best_vehicle.vehicle_id
        assigned[vehicle_id].append(order)
        remaining[vehicle_id] -= order.quantity_kg

    assignments = {
        vehicle_id: [order.order_id for order in vehicle_orders]
        for vehicle_id, vehicle_orders in assigned.items()
    }

    vehicle_routes = {}

    for vehicle in vehicles:
        vehicle_id = vehicle.vehicle_id
        vehicle_orders = assigned[vehicle_id]
        load = sum(order.quantity_kg for order in vehicle_orders)

        if vehicle_orders:
            route_result = get_route(vehicle_orders)
        else:
            route_result = {
                "feasible": True,
                "route": [depot],
                "objective_value": 0.0,
                "legs": [],
                "method": "No assigned orders",
            }

        vehicle_routes[vehicle_id] = {
            "route": route_result["route"],
            "feasible": route_result["feasible"],
            "distance_km": route_result["objective_value"],
            "orders": assignments[vehicle_id],
            "destinations": list(dict.fromkeys(
                order.destination for order in vehicle_orders
            )),
            "load_kg": round(load, 2),
            "capacity_kg": vehicle.capacity_kg,
            "remaining_capacity_kg": round(
                vehicle.capacity_kg - load, 2
            ),
            "utilization_percent": round(
                load / vehicle.capacity_kg * 100, 2
            ),
            "method": route_result["method"],
        }

    return {
        "feasible": not unassigned,
        "errors": [] if not unassigned else [
            "Some orders could not be assigned to a feasible vehicle."
        ],
        "assignments": assignments,
        "remaining_capacity_kg": {
            key: round(value, 2) for key, value in remaining.items()
        },
        "unassigned_orders": unassigned,
        "vehicle_routes": vehicle_routes,
    }
