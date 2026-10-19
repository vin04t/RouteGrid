
"""Tests for route-aware allocation."""

from core.allocation import (
    DeliveryOrder,
    Vehicle,
    allocate_orders_route_aware,
)
from core.network import build_network


def test_route_aware_allocation_respects_capacity():
    graph = build_network()
    orders = [
        DeliveryOrder("ORD-001", "Mumbai", 400),
        DeliveryOrder("ORD-002", "Delhi", 300),
        DeliveryOrder("ORD-003", "Hyderabad", 200),
        DeliveryOrder("ORD-004", "Bengaluru", 100),
    ]
    vehicles = [
        Vehicle("TRUCK-1", 500),
        Vehicle("TRUCK-2", 500),
    ]

    result = allocate_orders_route_aware(
        orders, vehicles, graph, depot="Pune"
    )

    assert result["feasible"] is True
    assert result["unassigned_orders"] == []

    for vehicle_id, route in result["vehicle_routes"].items():
        assert route["load_kg"] <= route["capacity_kg"]
        assert route["feasible"] is True


def test_orders_are_unassigned_when_fleet_capacity_is_too_small():
    graph = build_network()
    orders = [
        DeliveryOrder("ORD-001", "Mumbai", 900),
        DeliveryOrder("ORD-002", "Delhi", 900),
    ]
    vehicles = [Vehicle("TRUCK-1", 1000)]

    result = allocate_orders_route_aware(
        orders, vehicles, graph, depot="Pune"
    )

    assert result["feasible"] is False
    assert len(result["unassigned_orders"]) == 1


def test_orders_for_same_city_share_a_route_stop():
    graph = build_network()
    orders = [
        DeliveryOrder("ORD-001", "Mumbai", 100),
        DeliveryOrder("ORD-002", "Mumbai", 150),
    ]
    vehicles = [Vehicle("TRUCK-1", 500)]

    result = allocate_orders_route_aware(
        orders, vehicles, graph, depot="Pune"
    )

    assert result["feasible"] is True
    assert result["vehicle_routes"]["TRUCK-1"]["destinations"] == ["Mumbai"]


def test_orders_with_no_route_are_left_unassigned():
    """Road closures must not silently assign unreachable orders."""
    from core.network import get_available_graph

    graph = build_network()
    closed_roads = [edge for edge in list(graph.edges()) if "Pune" in edge]
    disconnected_graph = get_available_graph(graph, closed_roads)

    result = allocate_orders_route_aware(
        [DeliveryOrder("ORD-UNREACHABLE", "Delhi", 100)],
        [Vehicle("TRUCK-1", 500)],
        disconnected_graph,
        depot="Pune",
    )

    assert result["feasible"] is False
    assert result["unassigned_orders"] == ["ORD-UNREACHABLE"]
    assert result["assignments"]["TRUCK-1"] == []
