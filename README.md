# RouteGrid 🚚

**Pan-India Delivery Optimization and Logistics Resilience System**

RouteGrid is a software-only logistics simulator built with Python and Streamlit. It models a weighted network of Indian cities, plans delivery routes, simulates road closures, and compares two vehicle-allocation strategies. It is designed as a Discrete Mathematics course project demonstrating graph theory, shortest paths, combinatorics, and constraint validation.

> **Scope note:** Route distances, estimated travel times, and costs are illustrative values from a static educational network. RouteGrid does not use live maps, traffic, road conditions, or freight prices.

## Features

- **Single-delivery routing:** Find a shortest feasible route between a dispatch city and a destination.
- **Multi-stop planning:** Compare visiting orders for selected destinations and calculate the recommended route.
- **Optimization objectives:** Plan using distance, estimated time, or estimated cost.
- **Road-closure simulation:** Close selected links, recompute connectivity, and report when no feasible route remains.
- **Vehicle allocation:** Compare first-fit allocation with a route-aware heuristic subject to vehicle capacity limits.
- **Network Explorer:** Visualize the city network and inspect connected components.
- **Order management:** Work with delivery orders and vehicle capacities.
- **Exports:** Download route reports and allocation results as CSV files.
- **Discrete Mathematics view:** Connect the implementation to weighted graphs, shortest paths, counting, permutations, and logical validation.

## Technology stack

- Python
- Streamlit
- NetworkX
- Plotly
- Pandas
- NumPy
- Pytest

## Quick start

Python 3.10 or later is recommended.

```bash
git clone https://github.com/vin04t/RouteGrid.git
cd RouteGrid

python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m streamlit run app.py
```

Streamlit prints a local URL (usually `http://localhost:8501`) that you can open in your browser.

## Run the automated tests

```bash
python -m pytest core -v
```

The included tests cover allocation capacity checks, route-aware allocation, disconnected networks, a normal multi-stop route, and a route that does not return to the depot. The reviewed package has **10 automated tests**.

## How the algorithms are used

- **Weighted graph:** Cities are vertices and available road links are weighted edges.
- **Shortest path:** Dijkstra's algorithm is used to find minimum-weight routes in the currently available network.
- **Multi-stop order:** An exact permutation search evaluates candidate destination orders for the small number of stops supported by this educational prototype. Its runtime grows factorially, so it is not intended for large-scale production routing.
- **First-fit allocation:** Assigns orders to available vehicles in a simple greedy sequence while respecting capacity.
- **Route-aware allocation:** A greedy heuristic considers incremental route distance, vehicle capacity, balancing, and reuse penalties. It is a heuristic—not a proof of globally optimal fleet allocation.
- **Network resilience:** Connected-component analysis helps identify cities separated by simulated road closures.

## Project structure

```text
RouteGrid/
├── app.py
├── requirements.txt
├── TEST_REPORT.md
└── core/
    ├── __init__.py
    ├── allocation.py
    ├── network.py
    ├── optimizer.py
    ├── test_allocation.py
    ├── test_optimizer.py
    └── test_route_aware_allocation.py
```

## Limitations and future work

- Replace the illustrative network with validated geographic and road-distance data.
- Calibrate travel-time and cost estimates against a real data source before operational use.
- Evaluate the route-aware allocation heuristic against exact or metaheuristic baselines on larger test cases.
- Add persistent storage, user authentication, and deployment configuration if the project is extended beyond a course prototype.

## Academic use

RouteGrid is an educational prototype for demonstrating discrete-mathematical models in logistics. Its outputs should not be used for real delivery dispatch decisions.
