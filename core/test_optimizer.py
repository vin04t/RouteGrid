"""Regression tests for RouteGrid multi-stop route optimization."""

from core.network import build_network, get_available_graph
from core.optimizer import optimize_delivery_order


def test_disconnected_depot_returns_infeasible_instead_of_crashing():
    graph = build_network()
    closed_roads = [edge for edge in list(graph.edges()) if "Pune" in edge]
    graph = get_available_graph(graph, closed_roads)

    result = optimize_delivery_order(
        graph,
        depot="Pune",
        destinations=["Delhi"],
    )

    assert result["feasible"] is False
    assert result["route"] == []
    assert result["objective_value"] is None
    assert "No feasible route" in result["message"]


def test_normal_multi_stop_route_remains_feasible():
    result = optimize_delivery_order(
        build_network(),
        depot="Pune",
        destinations=["Mumbai", "Bengaluru", "Hyderabad"],
    )

    assert result["feasible"] is True
    assert result["route"][0] == "Pune"
    assert result["route"][-1] == "Pune"
    assert result["objective_value"] == 2260.0


def test_route_can_finish_without_returning_to_depot():
    result = optimize_delivery_order(
        build_network(),
        depot="Pune",
        destinations=["Mumbai", "Bengaluru"],
        return_to_depot=False,
    )

    assert result["feasible"] is True
    assert result["route"][0] == "Pune"
    assert result["route"][-1] != "Pune"
