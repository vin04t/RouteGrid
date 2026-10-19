
"""RouteGrid: Pan-India logistics optimization simulator."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.allocation import (
    DeliveryOrder,
    Vehicle,
    allocate_orders_greedily,
    allocate_orders_route_aware,
)
from core.network import (
    CITY_DATA,
    build_network,
    find_shortest_route,
    get_available_graph,
    get_network_summary,
)
from core.optimizer import optimize_delivery_order


st.set_page_config(
    page_title="RouteGrid | Logistics Optimizer",
    page_icon="🚚",
    layout="wide",
)

st.title("🚚 RouteGrid")
st.caption("Pan-India Delivery Optimization and Logistics Resilience System")
st.info(
    "Educational simulator. Distances, travel times and costs are "
    "illustrative estimates, not live road or freight data."
)

base_graph = build_network()
cities = sorted(base_graph.nodes())

# ---------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------
st.sidebar.header("Delivery Planning")

planning_mode = st.sidebar.radio(
    "Planning mode",
    ["Single delivery", "Multiple deliveries"],
)

origin = st.sidebar.selectbox(
    "Dispatch city",
    cities,
    index=cities.index("Pune") if "Pune" in cities else 0,
)

# Orders must be delivered somewhere other than the dispatch city.
delivery_cities = [city for city in cities if city != origin]

destinations = []
destination = None
return_to_depot = True

if planning_mode == "Single delivery":
    options = [city for city in cities if city != origin]
    default_destination = "Delhi" if "Delhi" in options else options[0]

    destination = st.sidebar.selectbox(
        "Delivery destination",
        options,
        index=options.index(default_destination),
    )
else:
    options = [city for city in cities if city != origin]
    defaults = [
        city for city in ["Mumbai", "Hyderabad", "Bengaluru"]
        if city in options
    ]

    destinations = st.sidebar.multiselect(
        "Delivery destinations",
        options,
        default=defaults,
    )

    return_to_depot = st.sidebar.checkbox(
        "Return to dispatch city",
        value=True,
    )

objective_label = st.sidebar.selectbox(
    "Optimization objective",
    [
        "Minimum distance",
        "Minimum estimated time",
        "Minimum estimated cost",
    ],
)

weight = {
    "Minimum distance": "distance_km",
    "Minimum estimated time": "travel_hours",
    "Minimum estimated cost": "cost_inr",
}[objective_label]

st.sidebar.subheader("Disruption Simulation")

road_options = [
    f"{a} — {b}" for a, b in base_graph.edges()
]

selected_closures = st.sidebar.multiselect(
    "Close roads",
    road_options,
)

closed_roads = [
    tuple(item.split(" — ", maxsplit=1))
    for item in selected_closures
]

active_graph = get_available_graph(base_graph, closed_roads)
summary = get_network_summary(active_graph)

# ---------------------------------------------------------
# Route planner calculation
# ---------------------------------------------------------
route_result = None
route_error = None

if planning_mode == "Single delivery":
    route_result = find_shortest_route(
        active_graph,
        origin,
        destination,
        weight=weight,
    )
else:
    try:
        route_result = optimize_delivery_order(
            active_graph,
            depot=origin,
            destinations=destinations,
            weight=weight,
            return_to_depot=return_to_depot,
        )
    except ValueError as exc:
        route_error = str(exc)


# ---------------------------------------------------------
# Tabs
# ---------------------------------------------------------
tab_route, tab_orders, tab_network, tab_math = st.tabs(
    [
        "Route Planner",
        "Order Management",
        "Network Explorer",
        "Mathematics",
    ]
)


# ---------------------------------------------------------
# Route Planner
# ---------------------------------------------------------
with tab_route:
    st.subheader("Delivery Route")

    if route_error:
        st.error(route_error)

    elif (
        planning_mode == "Multiple deliveries"
        and route_result
        and not route_result.get("feasible", True)
    ):
        st.error(
            route_result.get(
                "message",
                "No feasible route exists under the selected road closures.",
            )
        )

    elif (
        planning_mode == "Multiple deliveries"
        and not destinations
    ):
        st.info("Choose one or more delivery destinations to plan a route.")

    elif (
        planning_mode == "Single delivery"
        and route_result
        and not route_result.get("route")
    ):
        st.error(
            f"No available route from {origin} to {destination} "
            "under the selected road closures. Reopen a road and try again."
        )

    elif route_result and route_result.get("route"):
        if planning_mode == "Single delivery":
            metrics = route_result
            method = "Dijkstra's shortest-path algorithm"
            route_text = " → ".join(route_result["route"])
        else:
            metrics = {
                key: sum(leg[key] for leg in route_result["legs"])
                for key in ["distance_km", "travel_hours", "cost_inr"]
            }
            method = route_result["method"]
            route_text = " → ".join(route_result["route"])

        c1, c2, c3 = st.columns(3)
        c1.metric("Total distance", f'{metrics["distance_km"]:,.0f} km')
        c2.metric("Estimated travel", f'{metrics["travel_hours"]:,.1f} h')
        c3.metric("Estimated cost", f'₹{metrics["cost_inr"]:,.0f}')

        st.success("A feasible route was found.")
        st.markdown(f"**Recommended route:** {route_text}")
        st.caption(f"Planning method: {method}")

        report = (
            "RouteGrid Delivery Report\n"
            f"Dispatch city: {origin}\n"
            f"Objective: {objective_label}\n"
            f"Route: {route_text}\n"
            f"Distance (km): {metrics['distance_km']}\n"
            f"Estimated hours: {metrics['travel_hours']}\n"
            f"Estimated cost (INR): {metrics['cost_inr']}\n"
            f"Closed roads: {', '.join(selected_closures) or 'None'}\n"
        )

        st.download_button(
            "Download route report",
            report,
            file_name="routegrid_route_report.txt",
            mime="text/plain",
        )

    elif not route_error:
        st.info("Choose valid route settings to calculate a delivery plan.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Cities", summary["city_count"])
    c2.metric("Available roads", summary["road_count"])
    c3.metric("Connected components", summary["component_count"])

    if not summary["is_connected"]:
        st.warning("Some cities are disconnected from the network.")


# ---------------------------------------------------------
# Order management and fleet comparison
# ---------------------------------------------------------
with tab_orders:
    st.subheader("Order and Vehicle Management")
    st.write(
        "Allocate customer orders to a fleet, calculate individual routes, "
        "and compare two allocation strategies."
    )

    balance_weight = st.slider(
        "Vehicle-balancing preference",
        min_value=0,
        max_value=5000,
        value=1200,
        step=100,
        help=(
            "Higher values penalize high projected vehicle utilization. "
            "This may spread orders across more trucks, but does not "
            "guarantee the shortest overall fleet distance."
        ),
    )

    reuse_penalty = st.slider(
        "Penalty for reusing an assigned vehicle",
        min_value=0,
        max_value=1000,
        value=250,
        step=50,
        help="A higher value encourages considering currently unused vehicles.",
    )

    with st.form("order_form"):
        st.markdown("#### Customer orders")

        order_count = st.number_input(
            "Number of orders",
            min_value=1,
            max_value=30,
            value=5,
            step=1,
        )

        order_rows = []

        for index in range(int(order_count)):
            c1, c2, c3 = st.columns([1, 2, 1])

            with c1:
                order_id = st.text_input(
                    "Order ID",
                    value=f"ORD-{index + 1:03d}",
                    key=f"order_id_{index}",
                )

            with c2:
                dest = st.selectbox(
                    "Destination",
                    delivery_cities,
                    index=(index + 2) % len(delivery_cities),
                    key=f"order_dest_{index}",
                )

            with c3:
                quantity = st.number_input(
                    "Weight (kg)",
                    min_value=1.0,
                    max_value=50000.0,
                    value=100.0 + index * 50,
                    step=10.0,
                    key=f"order_weight_{index}",
                )

            order_rows.append((order_id, dest, quantity))

        st.markdown("#### Fleet")

        vehicle_count = st.number_input(
            "Number of vehicles",
            min_value=1,
            max_value=10,
            value=3,
            step=1,
        )

        vehicle_rows = []

        for index in range(int(vehicle_count)):
            c1, c2 = st.columns(2)

            with c1:
                vehicle_id = st.text_input(
                    "Vehicle ID",
                    value=f"TRUCK-{index + 1:02d}",
                    key=f"vehicle_id_{index}",
                )

            with c2:
                capacity = st.number_input(
                    "Capacity (kg)",
                    min_value=1.0,
                    max_value=100000.0,
                    value=1000.0,
                    step=100.0,
                    key=f"vehicle_capacity_{index}",
                )

            vehicle_rows.append((vehicle_id, capacity))

        submitted = st.form_submit_button("Compare fleet strategies")


    def calculate_vehicle_routes(assignments, orders, vehicles):
        """Calculate routes and metrics for an existing allocation."""
        order_lookup = {order.order_id: order for order in orders}
        vehicle_lookup = {vehicle.vehicle_id: vehicle for vehicle in vehicles}

        rows = []
        total_distance = 0.0
        used_vehicles = 0
        total_load = 0.0
        all_routes_feasible = True

        for vehicle_id, order_ids in assignments.items():
            vehicle = vehicle_lookup[vehicle_id]
            assigned_orders = [
                order_lookup[order_id]
                for order_id in order_ids
                if order_id in order_lookup
            ]

            load = sum(order.quantity_kg for order in assigned_orders)
            total_load += load

            if assigned_orders:
                # A vehicle carrying orders is in use even if its route is
                # currently infeasible because of simulated road closures.
                used_vehicles += 1
                unique_destinations = list(dict.fromkeys(
                    order.destination for order in assigned_orders
                ))

                route_result_for_vehicle = optimize_delivery_order(
                    active_graph,
                    depot=origin,
                    destinations=unique_destinations,
                    weight="distance_km",
                    return_to_depot=True,
                )

                feasible = route_result_for_vehicle["feasible"]

                if feasible:
                    route = route_result_for_vehicle["route"]
                    distance = float(
                        route_result_for_vehicle["objective_value"]
                    )
                    total_distance += distance
                else:
                    route = []
                    distance = None
                    all_routes_feasible = False

            else:
                route = [origin]
                distance = 0.0
                feasible = True

            rows.append({
                "Vehicle": vehicle_id,
                "Orders": ", ".join(order_ids) or "None",
                "Destinations": ", ".join(
                    dict.fromkeys(
                        order.destination for order in assigned_orders
                    )
                ) or "None",
                "Route": " → ".join(route) if route else "No feasible route",
                "Load (kg)": round(load, 2),
                "Capacity (kg)": vehicle.capacity_kg,
                "Remaining (kg)": round(vehicle.capacity_kg - load, 2),
                "Utilization (%)": round(
                    load / vehicle.capacity_kg * 100, 2
                ),
                "Distance (km)": round(distance, 2) if distance is not None else None,
                "Route feasible": feasible,
            })

        capacity_total = sum(v.capacity_kg for v in vehicles)
        fleet_utilization = (
            total_load / capacity_total * 100 if capacity_total else 0.0
        )

        return {
            "rows": rows,
            # Never present a partial sum as the fleet's total distance.
            "total_distance": (
                round(total_distance, 2) if all_routes_feasible else None
            ),
            "used_vehicles": used_vehicles,
            "total_load": round(total_load, 2),
            "fleet_utilization": round(fleet_utilization, 2),
            "routes_feasible": all_routes_feasible,
        }


    if submitted:
        orders = [
            DeliveryOrder(order_id.strip(), dest, quantity)
            for order_id, dest, quantity in order_rows
        ]

        vehicles = [
            Vehicle(vehicle_id.strip(), capacity)
            for vehicle_id, capacity in vehicle_rows
        ]

        # Validate unique IDs before running either strategy.
        validation_errors = []
        order_ids = [order.order_id for order in orders]
        vehicle_ids = [vehicle.vehicle_id for vehicle in vehicles]

        if any(not item for item in order_ids):
            validation_errors.append("Order IDs cannot be empty.")
        if len(set(order_ids)) != len(order_ids):
            validation_errors.append("Order IDs must be unique.")
        if any(not item for item in vehicle_ids):
            validation_errors.append("Vehicle IDs cannot be empty.")
        if len(set(vehicle_ids)) != len(vehicle_ids):
            validation_errors.append("Vehicle IDs must be unique.")
        if any(order.destination == origin for order in orders):
            validation_errors.append(
                "Order destinations must differ from the dispatch city. "
                "Choose another destination and submit again."
            )

        if validation_errors:
            for error in validation_errors:
                st.error(error)

        else:
            first_fit = allocate_orders_greedily(orders, vehicles)

            balanced = allocate_orders_route_aware(
                orders=orders,
                vehicles=vehicles,
                graph=active_graph,
                depot=origin,
                return_to_depot=True,
                balance_weight=float(balance_weight),
                reuse_penalty=float(reuse_penalty),
            )

            if balanced["errors"] and not balanced["vehicle_routes"]:
                for error in balanced["errors"]:
                    st.error(error)

            else:
                first_metrics = calculate_vehicle_routes(
                    first_fit["assignments"], orders, vehicles
                )
                balanced_metrics = calculate_vehicle_routes(
                    balanced["assignments"], orders, vehicles
                )

                if first_fit["unassigned_orders"]:
                    first_metrics["routes_feasible"] = False
                    first_metrics["total_distance"] = None

                if balanced["unassigned_orders"]:
                    balanced_metrics["routes_feasible"] = False
                    balanced_metrics["total_distance"] = None

                st.markdown("### Strategy comparison")

                c1, c2 = st.columns(2)

                with c1:
                    st.markdown("#### First-fit allocation")
                    st.metric(
                        "Total fleet distance",
                        (
                            f'{first_metrics["total_distance"]:,.0f} km'
                            if first_metrics["total_distance"] is not None
                            else "Incomplete plan"
                        ),
                    )
                    st.metric(
                        "Vehicles used",
                        f'{first_metrics["used_vehicles"]} / {len(vehicles)}',
                    )
                    st.metric(
                        "Fleet capacity utilization",
                        f'{first_metrics["fleet_utilization"]:.1f}%',
                    )

                with c2:
                    st.markdown("#### Balanced route-aware allocation")
                    st.metric(
                        "Total fleet distance",
                        (
                            f'{balanced_metrics["total_distance"]:,.0f} km'
                            if balanced_metrics["total_distance"] is not None
                            else "Incomplete plan"
                        ),
                    )
                    st.metric(
                        "Vehicles used",
                        f'{balanced_metrics["used_vehicles"]} / {len(vehicles)}',
                    )
                    st.metric(
                        "Fleet capacity utilization",
                        f'{balanced_metrics["fleet_utilization"]:.1f}%',
                    )

                if first_fit["unassigned_orders"]:
                    st.warning(
                        "First-fit could not assign these orders: "
                        + ", ".join(first_fit["unassigned_orders"])
                    )

                if not first_metrics["routes_feasible"]:
                    st.warning(
                        "First-fit has an incomplete delivery plan. At least "
                        "one order is unassigned or one route is unreachable; "
                        "its total distance is not reported."
                    )

                if not balanced_metrics["routes_feasible"]:
                    st.warning(
                        "Balanced route-aware allocation has an incomplete "
                        "delivery plan. At least one order is unassigned or "
                        "one route is unreachable; its total distance is not reported."
                    )

                if (
                    first_metrics["total_distance"] is None
                    or balanced_metrics["total_distance"] is None
                ):
                    distance_difference = None
                    st.info(
                        "A distance comparison is unavailable until both "
                        "strategies produce complete, reachable delivery plans."
                    )
                else:
                    distance_difference = (
                        balanced_metrics["total_distance"]
                        - first_metrics["total_distance"]
                    )

                if distance_difference is None:
                    pass
                elif distance_difference < 0:
                    st.success(
                        f"Balanced allocation reduces simulated fleet "
                        f"distance by {abs(distance_difference):,.0f} km."
                    )
                elif distance_difference > 0:
                    st.info(
                        f"Balanced allocation adds {distance_difference:,.0f} km "
                        "in this scenario. The strategy trades distance for "
                        "different vehicle utilization."
                    )
                else:
                    st.info(
                        "Both strategies produce the same total simulated distance."
                    )

                comparison_df = pd.DataFrame([
                    {
                        "Strategy": "First-fit",
                        "Vehicles used": first_metrics["used_vehicles"],
                        "Total distance (km)": first_metrics["total_distance"],
                        "Fleet utilization (%)": first_metrics["fleet_utilization"],
                    },
                    {
                        "Strategy": "Balanced route-aware",
                        "Vehicles used": balanced_metrics["used_vehicles"],
                        "Total distance (km)": balanced_metrics["total_distance"],
                        "Fleet utilization (%)": balanced_metrics["fleet_utilization"],
                    },
                ])

                st.dataframe(
                    comparison_df,
                    use_container_width=True,
                    hide_index=True,
                )

                st.markdown("### Balanced allocation details")

                details_df = pd.DataFrame(balanced_metrics["rows"])
                st.dataframe(
                    details_df,
                    use_container_width=True,
                    hide_index=True,
                )

                st.markdown("### Individual vehicle plans")

                for row in balanced_metrics["rows"]:
                    with st.expander(
                        f'{row["Vehicle"]} — route details'
                    ):
                        if row["Orders"] == "None":
                            st.write("No orders assigned.")
                            continue

                        st.write(f'**Orders:** {row["Orders"]}')
                        st.write(f'**Route:** {row["Route"]}')

                        c1, c2, c3 = st.columns(3)
                        row_distance = row["Distance (km)"]
                        c1.metric(
                            "Distance",
                            f"{row_distance:,.0f} km"
                            if row_distance is not None
                            else "Unavailable",
                        )
                        c2.metric("Load", f'{row["Load (kg)"]:,.0f} kg')
                        c3.metric(
                            "Capacity used",
                            f'{row["Utilization (%)"]:.1f}%',
                        )

                if balanced["unassigned_orders"]:
                    st.error(
                        "Unassigned orders: "
                        + ", ".join(balanced["unassigned_orders"])
                    )

                st.download_button(
                    "Download balanced allocation CSV",
                    details_df.to_csv(index=False),
                    file_name="routegrid_balanced_allocation.csv",
                    mime="text/csv",
                )

                st.caption(
                    "Both strategies use simulated route distances. "
                    "The route-aware allocator is a heuristic and does not "
                    "guarantee a globally optimal fleet plan."
                )


# ---------------------------------------------------------
# Network Explorer
# ---------------------------------------------------------
with tab_network:
    st.subheader("Indian Logistics Network")

    fig = go.Figure()

    for city_a, city_b, data in active_graph.edges(data=True):
        a = CITY_DATA[city_a]
        b = CITY_DATA[city_b]

        fig.add_trace(go.Scatter(
            x=[a["lon"], b["lon"]],
            y=[a["lat"], b["lat"]],
            mode="lines",
            line={"width": 1.5},
            hovertemplate=(
                f"{city_a} ↔ {city_b}<br>"
                f"Distance: {data['distance_km']} km<extra></extra>"
            ),
            showlegend=False,
        ))

    fig.add_trace(go.Scatter(
        x=[CITY_DATA[city]["lon"] for city in cities],
        y=[CITY_DATA[city]["lat"] for city in cities],
        mode="markers+text",
        text=cities,
        textposition="top center",
        marker={"size": 10},
        hovertemplate="%{text}<extra></extra>",
        name="Cities",
    ))

    fig.update_layout(
        height=650,
        xaxis_title="Longitude",
        yaxis_title="Latitude",
        template="plotly_dark",
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)

    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Schematic network with approximate coordinates, not verified road geometry."
    )


# ---------------------------------------------------------
# Discrete Mathematics
# ---------------------------------------------------------
with tab_math:
    st.subheader("Discrete Mathematics in RouteGrid")

    st.markdown(
        """
        **1. Graph theory:** Cities are vertices and transport links are
        weighted edges. Dijkstra's algorithm finds minimum-weight paths.

        **2. Counting and combinatorics:** For `n` cities, there are
        `n × (n − 1) / 2` possible undirected city pairs. For `k` delivery
        destinations, there are `k!` possible visiting orders.

        **3. Logic and validation:** Orders must have unique IDs and positive
        quantities. Allocations must respect vehicle capacity, and routes must
        use available connections.
        """
    )

    st.write(
        f"Network connected: "
        f"**{'Yes' if summary['is_connected'] else 'No'}**"
    )

    for index, component in enumerate(summary["components"], start=1):
        with st.expander(
            f"Connected component {index} ({len(component)} cities)"
        ):
            st.write(", ".join(component))
