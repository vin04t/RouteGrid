# RouteGrid Test Report

**Review date:** 18 October 2026

## Automated tests

Command: `python -m pytest core -v`

Result: **10 passed**

Coverage includes:
- Single-vehicle capacity checks and first-fit order allocation.
- Route-aware capacity limits and grouping orders for the same destination.
- Multi-stop optimization when roads disconnect the depot.
- A normal multi-stop route and a route that does not return to the depot.
- Orders to unreachable destinations remaining unassigned after simulated road closures.

## Additional checks

- Python syntax compilation passed for `app.py` and the `core` modules.
- Normal multi-stop scenario (Pune, Mumbai, Bengaluru, Hyderabad, return to Pune): feasible, 2,260 km.
- Closing every road incident to Pune: single-route search returned no route; multi-stop optimizer returned infeasible; route-aware allocation left the order unassigned.
- Capacity invariant passed in the route-aware allocation smoke test.

## Dashboard changes in this review

- Unreachable single and multi-stop routes now show an explicit error in the Route Planner.
- Fleet order destinations exclude the selected dispatch city, with a validation check as a safeguard.
- Fleet totals are shown as incomplete instead of displaying a partial route-distance sum as the full fleet total.
- The dashboard reports route-distance comparison as unavailable whenever either strategy has unassigned orders or unreachable routes.

## Verification limitation

The review environment did not have Streamlit installed and could not access the package index to install it. Therefore, dashboard launch and interactive browser behavior still need to be confirmed locally with `python -m streamlit run app.py`. The automated algorithm tests and Python compilation were run successfully.

## Run locally

```bash
source .venv/bin/activate
python -m pytest core -v
python -m streamlit run app.py
```
