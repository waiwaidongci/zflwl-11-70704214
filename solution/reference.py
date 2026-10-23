#!/usr/bin/env python3
"""Inverse-optimization reference solver for maintenance planning."""

from __future__ import annotations

import itertools
import json
import math
import re
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable


TOP_KEYS = {"held_out", "histories", "schema"}
HISTORY_KEYS = {
    "cards",
    "history_id",
    "machines",
    "observed_optima",
    "orders",
    "shift",
}
BATCH_KEYS = {"batch_id", "cards", "machines", "orders", "shift"}
PACKAGE_KEYS = {"cards", "machines", "orders", "shift"}
PLAN_KEYS = {"carding", "pairing", "route"}
MACHINE_ID = re.compile(r"MACHINE-[A-Z0-9]{2}\Z")
CARD_ID = re.compile(r"CARD-[A-Z0-9]{2}\Z")
ORDER_ID = re.compile(r"WO-[A-Z0-9]{4}\Z")
HISTORY_ID = re.compile(r"HIST-[0-9]{2}\Z")
BATCH_ID = re.compile(r"BATCH-[A-Z0-9]{2}\Z")
COMPONENTS = ("skill", "setup", "travel", "tardiness")


class Refused(ValueError):
    """The input cannot produce a unique inverse plan."""


def _integer(value: Any, label: str, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise Refused(f"{label} is not an integer")
    if value < 0 or (positive and value == 0):
        raise Refused(f"{label} is outside its domain")
    return value


def _signed_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise Refused(f"{label} is not an integer")
    return value


def _vector(value: Any, length: int, label: str) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) != length:
        raise Refused(f"{label} must contain {length} integers")
    return tuple(_signed_integer(item, label) for item in value)


def _window(value: Any, label: str) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2:
        raise Refused(f"{label} must contain two timestamps")
    opened = _integer(value[0], f"{label} open_min")
    closed = _integer(value[1], f"{label} close_min")
    if opened >= closed:
        raise Refused(f"{label} must open before it closes")
    return (opened, closed)


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise Refused("duplicate JSON keys are invalid")
        result[key] = value
    return result


def _object(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise Refused(f"{label} keys are invalid")
    return value


def _parse_package(
    raw: Any,
    *,
    machine_count: int,
    label: str,
) -> dict[str, Any]:
    package = _object(raw, PACKAGE_KEYS, f"{label} package")
    raw_machines = package["machines"]
    if not isinstance(raw_machines, list) or len(raw_machines) != machine_count:
        raise Refused(f"{label} machines must contain {machine_count} entries")
    machines: list[dict[str, Any]] = []
    machine_ids: set[str] = set()
    for item in raw_machines:
        machine = _object(item, {"machine_id", "x", "y"}, f"{label} machine")
        machine_id = machine["machine_id"]
        if not isinstance(machine_id, str) or MACHINE_ID.fullmatch(machine_id) is None:
            raise Refused("machine id is invalid")
        if machine_id in machine_ids:
            raise Refused("machine ids must be unique within one package")
        machine_ids.add(machine_id)
        machines.append(
            {
                "machine_id": machine_id,
                "x": _integer(machine["x"], "machine x"),
                "y": _integer(machine["y"], "machine y"),
            }
        )
    machines.sort(key=lambda item: item["machine_id"])

    raw_cards = package["cards"]
    if not isinstance(raw_cards, list) or len(raw_cards) != machine_count:
        raise Refused(f"{label} cards must contain {machine_count} entries")
    cards: list[dict[str, Any]] = []
    card_ids: set[str] = set()
    for item in raw_cards:
        card = _object(item, {"card_id", "signature", "windows"}, f"{label} card")
        card_id = card["card_id"]
        if not isinstance(card_id, str) or CARD_ID.fullmatch(card_id) is None:
            raise Refused("card id is invalid")
        if card_id in card_ids:
            raise Refused("card ids must be unique within one package")
        card_ids.add(card_id)
        raw_windows = card["windows"]
        if not isinstance(raw_windows, list) or len(raw_windows) != 2:
            raise Refused("windows must contain exactly two intervals")
        windows = [
            _window(raw_windows[0], "first window"),
            _window(raw_windows[1], "second window"),
        ]
        if max(opened for opened, _ in windows) >= min(
            closed for _, closed in windows
        ):
            raise Refused("windows must overlap")
        cards.append(
            {
                "card_id": card_id,
                "signature": _vector(card["signature"], 6, "signature"),
                "windows": windows,
            }
        )
    cards.sort(key=lambda item: item["card_id"])

    order_count = machine_count * 2
    raw_orders = package["orders"]
    if not isinstance(raw_orders, list) or len(raw_orders) != order_count:
        raise Refused(f"{label} orders must contain {order_count} entries")
    orders: list[dict[str, Any]] = []
    order_ids: set[str] = set()
    for item in raw_orders:
        order = _object(
            item,
            {"order_id", "symptom", "duration_min", "due_min", "weight"},
            f"{label} order",
        )
        order_id = order["order_id"]
        if not isinstance(order_id, str) or ORDER_ID.fullmatch(order_id) is None:
            raise Refused("order id is invalid")
        if order_id in order_ids:
            raise Refused("order ids must be unique within one package")
        order_ids.add(order_id)
        orders.append(
            {
                "order_id": order_id,
                "symptom": _vector(order["symptom"], 6, "symptom"),
                "duration_min": _integer(
                    order["duration_min"], "duration_min", positive=True
                ),
                "due_min": _integer(order["due_min"], "due_min"),
                "weight": _integer(order["weight"], "weight", positive=True),
            }
        )
    orders.sort(key=lambda item: item["order_id"])

    shift = _object(
        package["shift"],
        {"start_min", "travel_min_per_unit", "depot_x", "depot_y"},
        f"{label} shift",
    )
    parsed_shift = {
        "start_min": _integer(shift["start_min"], "start_min"),
        "travel_min_per_unit": _integer(
            shift["travel_min_per_unit"],
            "travel_min_per_unit",
            positive=True,
        ),
        "depot_x": _integer(shift["depot_x"], "depot_x"),
        "depot_y": _integer(shift["depot_y"], "depot_y"),
    }
    return {
        "machines": machines,
        "cards": cards,
        "orders": orders,
        "shift": parsed_shift,
    }


def _parse_plan(
    raw: Any,
    package: dict[str, Any],
    label: str,
) -> tuple[tuple[int, ...], tuple[tuple[int, int], ...], tuple[int, ...]]:
    plan = _object(raw, PLAN_KEYS, f"{label} plan")
    machines = package["machines"]
    cards = package["cards"]
    orders = package["orders"]
    machine_by_id = {item["machine_id"]: index for index, item in enumerate(machines)}
    card_by_id = {item["card_id"]: index for index, item in enumerate(cards)}
    order_by_id = {item["order_id"]: index for index, item in enumerate(orders)}

    carding = plan["carding"]
    if not isinstance(carding, dict) or set(carding) != set(card_by_id):
        raise Refused(f"{label} carding keys are invalid")
    if any(not isinstance(value, str) for value in carding.values()):
        raise Refused(f"{label} carding values must be machine ids")
    inverse_card: dict[int, int] = {}
    for card_id, machine_id in carding.items():
        if machine_id not in machine_by_id:
            raise Refused(f"{label} carding names an unknown machine")
        machine_index = machine_by_id[machine_id]
        if machine_index in inverse_card:
            raise Refused(f"{label} carding must be a bijection")
        inverse_card[machine_index] = card_by_id[card_id]
    card_mapping = tuple(inverse_card[index] for index in range(len(machines)))

    pairing = plan["pairing"]
    if not isinstance(pairing, dict) or set(pairing) != set(order_by_id):
        raise Refused(f"{label} pairing keys are invalid")
    if any(not isinstance(value, str) for value in pairing.values()):
        raise Refused(f"{label} pairing values must be machine ids")
    groups: list[list[int]] = [[] for _ in machines]
    for order_id, machine_id in pairing.items():
        if machine_id not in machine_by_id:
            raise Refused(f"{label} pairing names an unknown machine")
        groups[machine_by_id[machine_id]].append(order_by_id[order_id])
    if any(len(group) != 2 for group in groups):
        raise Refused(f"{label} pairing must put two orders on every machine")
    pieces = tuple((min(group), max(group)) for group in groups)

    route = plan["route"]
    if not isinstance(route, list) or len(route) != len(orders):
        raise Refused(f"{label} route must cover every order exactly once")
    if any(
        not isinstance(order_id, str) or order_id not in order_by_id
        for order_id in route
    ):
        raise Refused(f"{label} route contains an unknown order id")
    if len(set(route)) != len(route):
        raise Refused(f"{label} route repeats an order id")
    route_indices = tuple(order_by_id[order_id] for order_id in route)
    block_machines = tuple(
        machine_by_id[pairing[orders[index]["order_id"]]]
        for index in route_indices[::2]
    )
    if len(set(block_machines)) != len(machines):
        raise Refused(f"{label} route must visit every machine block once")
    for position, machine_index in enumerate(block_machines):
        expected = tuple(sorted(groups[machine_index]))
        actual = tuple(sorted(route_indices[position * 2 : position * 2 + 2]))
        if actual != expected:
            raise Refused(f"{label} route splits or mixes a machine block")
    return (card_mapping, pieces, route_indices)


def parse_payload(path: Path) -> dict[str, Any]:
    """Read the inverse planning package and reject malformed contracts."""
    try:
        raw = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_no_duplicate_keys,
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise Refused("input JSON is unreadable") from exc
    payload = _object(raw, TOP_KEYS, "top-level")
    if payload["schema"] != "inverse-maint-v1":
        raise Refused("schema is unsupported")

    raw_histories = payload["histories"]
    if not isinstance(raw_histories, list) or len(raw_histories) != 3:
        raise Refused("histories must contain exactly three entries")
    histories: list[dict[str, Any]] = []
    history_ids: set[str] = set()
    for raw_history in raw_histories:
        history = _object(raw_history, HISTORY_KEYS, "history")
        history_id = history["history_id"]
        if (
            not isinstance(history_id, str)
            or HISTORY_ID.fullmatch(history_id) is None
        ):
            raise Refused("history id is invalid")
        if history_id in history_ids:
            raise Refused("history ids must be unique")
        history_ids.add(history_id)
        package = _parse_package(
            {key: history[key] for key in PACKAGE_KEYS},
            machine_count=2,
            label=history_id,
        )
        raw_observed = history["observed_optima"]
        if not isinstance(raw_observed, list) or len(raw_observed) != 2:
            raise Refused(f"{history_id} observed_optima must contain two plans")
        observed = [
            _parse_plan(item, package, history_id) for item in raw_observed
        ]
        if len(set(observed)) != 2:
            raise Refused(f"{history_id} observed plans must be distinct")
        histories.append(
            {
                "history_id": history_id,
                "package": package,
                "observed": observed,
            }
        )

    held_out = _object(payload["held_out"], BATCH_KEYS, "held_out")
    batch_id = held_out["batch_id"]
    if not isinstance(batch_id, str) or BATCH_ID.fullmatch(batch_id) is None:
        raise Refused("held_out batch id is invalid")
    held_package = _parse_package(
        {key: held_out[key] for key in PACKAGE_KEYS},
        machine_count=3,
        label="held_out",
    )
    return {
        "histories": histories,
        "held_out": held_package,
    }


def _pairings(items: tuple[int, ...]) -> Iterable[tuple[tuple[int, int], ...]]:
    if not items:
        yield ()
        return
    first = items[0]
    for position in range(1, len(items)):
        second = items[position]
        rest = items[1:position] + items[position + 1 :]
        for suffix in _pairings(rest):
            yield ((first, second),) + suffix


def _earliest_start(
    arrival: int,
    duration: int,
    windows: list[tuple[int, int]],
) -> int | None:
    eligible = []
    for opened, closed in windows:
        start = max(arrival, opened)
        if start + duration <= closed:
            eligible.append(start)
    return min(eligible) if eligible else None


def enumerate_candidates(package: dict[str, Any]) -> list[dict[str, Any]]:
    """List every feasible plan and its four raw cost components."""
    machines = package["machines"]
    cards = package["cards"]
    orders = package["orders"]
    shift = package["shift"]
    machine_count = len(machines)
    order_count = len(orders)
    coordinates = [(item["x"], item["y"]) for item in machines]
    depot = (shift["depot_x"], shift["depot_y"])
    durations = [item["duration_min"] for item in orders]
    due = [item["due_min"] for item in orders]
    weights = [item["weight"] for item in orders]
    symptoms = [item["symptom"] for item in orders]

    candidates: list[dict[str, Any]] = []
    for card_mapping in itertools.permutations(range(machine_count)):
        for pieces in _pairings(tuple(range(order_count))):
            skill_penalty = 0
            for machine_index, (first, second) in enumerate(pieces):
                signature = cards[card_mapping[machine_index]]["signature"]
                for axis in range(6):
                    skill_penalty += (
                        symptoms[first][axis]
                        + symptoms[second][axis]
                        - 2 * signature[axis]
                    ) ** 2
            for machine_path in itertools.permutations(range(machine_count)):
                for flips in itertools.product((False, True), repeat=machine_count):
                    time = shift["start_min"]
                    setup_total = 0
                    travel_total = 0
                    tardiness = 0
                    previous_order = -1
                    previous_machine = -1
                    route: list[int] = []
                    feasible = True
                    for machine_index, flip in zip(machine_path, flips):
                        first, second = pieces[machine_index]
                        if flip:
                            first, second = second, first
                        source = (
                            depot
                            if previous_machine < 0
                            else coordinates[previous_machine]
                        )
                        target = coordinates[machine_index]
                        leg = shift["travel_min_per_unit"] * (
                            abs(source[0] - target[0])
                            + abs(source[1] - target[1])
                        )
                        setup_minutes = (
                            0
                            if previous_order < 0
                            else 2
                            + abs(
                                symptoms[previous_order][2]
                                - symptoms[first][2]
                            )
                            + abs(
                                symptoms[previous_order][5]
                                - symptoms[first][5]
                            )
                        )
                        duration = durations[first] + durations[second]
                        start = _earliest_start(
                            time + leg + setup_minutes,
                            duration,
                            cards[card_mapping[machine_index]]["windows"],
                        )
                        if start is None:
                            feasible = False
                            break
                        first_finish = start + durations[first]
                        second_finish = first_finish + durations[second]
                        tardiness += (
                            max(0, first_finish - due[first]) * weights[first]
                            + max(0, second_finish - due[second]) * weights[second]
                        )
                        travel_total += leg
                        setup_total += setup_minutes
                        time = second_finish
                        previous_order = second
                        previous_machine = machine_index
                        route.extend((first, second))
                    if not feasible:
                        continue
                    route_tuple = tuple(route)
                    card_sequence = tuple(
                        card_mapping[index] for index in machine_path
                    )
                    candidates.append(
                        {
                            "card_mapping": card_mapping,
                            "pieces": pieces,
                            "machine_path": machine_path,
                            "flips": flips,
                            "route": route_tuple,
                            "components": (
                                skill_penalty,
                                setup_total,
                                travel_total,
                                tardiness,
                            ),
                            "canonical_key": (
                                route_tuple,
                                card_sequence,
                                machine_path,
                            ),
                        }
                    )
    return candidates


def _dot(weights: tuple[int, int, int, int], costs: tuple[int, ...]) -> int:
    return sum(weight * cost for weight, cost in zip(weights, costs))


def _rank(rows: list[tuple[int, ...]]) -> int:
    matrix = [[Fraction(value) for value in row] for row in rows]
    rank = 0
    for column in range(len(COMPONENTS)):
        pivot = next(
            (row for row in range(rank, len(matrix)) if matrix[row][column]),
            None,
        )
        if pivot is None:
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        divisor = matrix[rank][column]
        matrix[rank] = [value / divisor for value in matrix[rank]]
        for row in range(len(matrix)):
            if row == rank:
                continue
            factor = matrix[row][column]
            if factor:
                matrix[row] = [
                    value - factor * pivot_value
                    for value, pivot_value in zip(matrix[row], matrix[rank])
                ]
        rank += 1
    return rank


def _primitive_null_vector(rows: list[tuple[int, ...]]) -> tuple[int, ...]:
    matrix = [[Fraction(value) for value in row] for row in rows]
    rank = 0
    pivots: list[int] = []
    for column in range(len(COMPONENTS)):
        pivot = next(
            (row for row in range(rank, len(matrix)) if matrix[row][column]),
            None,
        )
        if pivot is None:
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        divisor = matrix[rank][column]
        matrix[rank] = [value / divisor for value in matrix[rank]]
        for row in range(len(matrix)):
            if row == rank:
                continue
            factor = matrix[row][column]
            if factor:
                matrix[row] = [
                    value - factor * pivot_value
                    for value, pivot_value in zip(matrix[row], matrix[rank])
                ]
        pivots.append(column)
        rank += 1
    free = next(
        column for column in range(len(COMPONENTS)) if column not in pivots
    )
    vector = [Fraction(0) for _ in COMPONENTS]
    vector[free] = Fraction(1)
    for row in range(rank - 1, -1, -1):
        pivot = pivots[row]
        vector[pivot] = -sum(
            matrix[row][column] * vector[column]
            for column in range(pivot + 1, len(COMPONENTS))
        )
    denominator = 1
    for value in vector:
        denominator = math.lcm(denominator, value.denominator)
    integers = [int(value * denominator) for value in vector]
    common = math.gcd(*[abs(value) for value in integers])
    integers = [value // common for value in integers]
    if integers[0] < 0:
        integers = [-value for value in integers]
    return tuple(integers)


def _canonical_plan(
    package: dict[str, Any],
    candidate: dict[str, Any],
) -> tuple[dict[str, str], dict[str, str], list[str]]:
    machines = package["machines"]
    cards = package["cards"]
    orders = package["orders"]
    carding = {
        cards[card_index]["card_id"]: machines[machine_index]["machine_id"]
        for machine_index, card_index in enumerate(candidate["card_mapping"])
    }
    pairing: dict[str, str] = {}
    for machine_index, (first, second) in enumerate(candidate["pieces"]):
        machine_id = machines[machine_index]["machine_id"]
        pairing[orders[first]["order_id"]] = machine_id
        pairing[orders[second]["order_id"]] = machine_id
    route = [orders[index]["order_id"] for index in candidate["route"]]
    return dict(sorted(carding.items())), dict(sorted(pairing.items())), route


def _candidate_plan_key(
    observed: tuple[
        tuple[int, ...],
        tuple[tuple[int, int], ...],
        tuple[int, ...],
    ],
) -> tuple[
    tuple[int, ...],
    tuple[tuple[int, int], ...],
    tuple[int, ...],
]:
    return observed


def solve(payload: dict[str, Any]) -> dict[str, Any]:
    """Recover primitive objective weights and solve the held-out package."""
    history_candidates: list[list[dict[str, Any]]] = []
    equalities: list[tuple[int, ...]] = []
    observed_costs: list[list[tuple[int, ...]]] = []
    observed_keys: list[set[tuple[Any, ...]]] = []
    for history in payload["histories"]:
        package = history["package"]
        candidates = enumerate_candidates(package)
        candidate_by_plan = {
            _candidate_plan_key(
                (
                    item["card_mapping"],
                    item["pieces"],
                    item["route"],
                )
            ): item
            for item in candidates
        }
        costs: list[tuple[int, ...]] = []
        keys: set[tuple[Any, ...]] = set()
        for plan in history["observed"]:
            candidate = candidate_by_plan.get(_candidate_plan_key(plan))
            if candidate is None:
                raise Refused("an observed optimal plan is infeasible")
            costs.append(candidate["components"])
            keys.add(candidate["canonical_key"])
        for other in costs[1:]:
            equalities.append(
                tuple(other[index] - costs[0][index] for index in range(4))
            )
        history_candidates.append(candidates)
        observed_costs.append(costs)
        observed_keys.append(keys)

    rank = _rank(equalities)
    if rank != 3:
        raise Refused("observed ties do not determine one weight ray")
    weights = _primitive_null_vector(equalities)
    if any(weight <= 0 or weight > 999 for weight in weights):
        raise Refused("the recovered weights are outside the primitive range")
    if math.gcd(*weights) != 1:
        raise Refused("the recovered weights are not primitive")

    margins: list[int] = []
    for candidates, costs, wanted in zip(
        history_candidates,
        observed_costs,
        observed_keys,
    ):
        objectives = {
            item["canonical_key"]: _dot(weights, item["components"])
            for item in candidates
        }
        best = min(objectives.values())
        optimal_keys = {
            key for key, value in objectives.items() if value == best
        }
        if wanted != optimal_keys:
            raise Refused("observed_optima must list every primary-optimal plan")
        if any(_dot(weights, cost) != best for cost in costs):
            raise Refused("the recovered weights do not tie every observed plan")
        strict = [value for value in objectives.values() if value > best]
        if not strict:
            raise Refused("a history has no strict certificate margin")
        margins.append(min(strict) - best)

    held_package = payload["held_out"]
    held_candidates = enumerate_candidates(held_package)
    if not held_candidates:
        raise Refused("the held-out package has no feasible maintenance plan")

    def held_key(item: dict[str, Any]) -> tuple[Any, ...]:
        route_ids = tuple(
            held_package["orders"][index]["order_id"] for index in item["route"]
        )
        block_cards = tuple(
            held_package["cards"][item["card_mapping"][machine_index]]["card_id"]
            for machine_index in item["machine_path"]
        )
        machine_ids = tuple(
            held_package["machines"][index]["machine_id"]
            for index in item["machine_path"]
        )
        return (
            _dot(weights, item["components"]),
            route_ids,
            block_cards,
            machine_ids,
        )

    best = min(held_candidates, key=held_key)
    carding, pairing, route = _canonical_plan(held_package, best)
    skill_penalty, setup_total, travel_total, tardiness = best["components"]
    objective = _dot(weights, best["components"])
    return {
        "status": "ok",
        "weights": {
            "setup": weights[1],
            "skill": weights[0],
            "tardiness": weights[3],
            "travel": weights[2],
        },
        "certificate": {
            "equality_rank": rank,
            "margins": margins,
        },
        "plan": {
            "carding": carding,
            "pairing": pairing,
            "route": route,
            "metrics": {
                "objective": objective,
                "skill_penalty": skill_penalty,
                "total_setup": setup_total,
                "total_travel": travel_total,
                "weighted_tardiness": tardiness,
            },
        },
    }


def main() -> int:
    if len(sys.argv) != 3:
        print("REFUSED: expected input and output paths", file=sys.stderr)
        return 2
    source = Path(sys.argv[1])
    target = Path(sys.argv[2])
    try:
        payload = parse_payload(source)
        result = solve(payload)
    except Refused as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    try:
        target.write_text(
            json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    except OSError:
        print("REFUSED: output path cannot be written", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
