
"""Tests for RouteGrid allocation functions."""

from core.allocation import (
    DeliveryOrder,
    Vehicle,
    allocate_orders_greedily,
    allocate_orders_to_vehicle,
)


def test_single_vehicle_fits_orders():
    orders = [
        DeliveryOrder("ORD-001", "Mumbai", 100),
        DeliveryOrder("ORD-002", "Delhi", 200),
    ]
    vehicle = Vehicle("TRUCK-1", 500)

    result = allocate_orders_to_vehicle(orders, vehicle)

    assert result["feasible"] is True
    assert result["total_weight_kg"] == 300
    assert result["remaining_capacity_kg"] == 200


def test_single_vehicle_rejects_over_capacity():
    orders = [
        DeliveryOrder("ORD-001", "Mumbai", 400),
        DeliveryOrder("ORD-002", "Delhi", 300),
    ]
    vehicle = Vehicle("TRUCK-1", 500)

    result = allocate_orders_to_vehicle(orders, vehicle)

    assert result["feasible"] is False
    assert result["total_weight_kg"] == 700


def test_greedy_allocation_assigns_orders():
    orders = [
        DeliveryOrder("ORD-001", "Mumbai", 400),
        DeliveryOrder("ORD-002", "Delhi", 300),
        DeliveryOrder("ORD-003", "Pune", 200),
    ]
    vehicles = [
        Vehicle("TRUCK-1", 500),
        Vehicle("TRUCK-2", 500),
    ]

    result = allocate_orders_greedily(orders, vehicles)

    assert result["feasible"] is True
    assert result["unassigned_orders"] == []
