from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
from pathlib import Path


ENTRY = os.environ.get("MAINT_PLANNER", "/app/plan_maintenance.py")

SAFE_ENV = {
    "PATH": "/usr/bin:/bin",
    "HOME": "/tmp",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
}


def _run(payload: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-S", "-P", "-B", ENTRY, str(payload), str(output)],
        text=True,
        capture_output=True,
        env=SAFE_ENV,
        timeout=15,
        check=False,
    )


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _record_pass(*case_ids: str) -> None:
    print("\nPASS " + " ".join(case_ids).replace("FAILED ", ""))


def _history_zero() -> dict[str, object]:
    return {
        "history_id": "HIST-00",
        "machines": [
            {"machine_id": "MACHINE-00", "x": 4, "y": 1},
            {"machine_id": "MACHINE-01", "x": 0, "y": 5},
        ],
        "cards": [
            {
                "card_id": "CARD-00",
                "signature": [1, 3, 4, 2, 6, 0],
                "windows": [[0, 400], [50, 500]],
            },
            {
                "card_id": "CARD-01",
                "signature": [0, -1, -1, -2, 2, 5],
                "windows": [[0, 400], [50, 500]],
            },
        ],
        "orders": [
            {
                "order_id": "WO-0000",
                "symptom": [6, 5, 3, 6, 0, 4],
                "duration_min": 20,
                "due_min": 15,
                "weight": 3,
            },
            {
                "order_id": "WO-0001",
                "symptom": [4, 3, 1, 1, 1, 2],
                "duration_min": 10,
                "due_min": 30,
                "weight": 1,
            },
            {
                "order_id": "WO-0002",
                "symptom": [0, 0, 2, 2, 2, 3],
                "duration_min": 10,
                "due_min": 15,
                "weight": 2,
            },
            {
                "order_id": "WO-0003",
                "symptom": [3, 2, 1, 0, 5, 2],
                "duration_min": 20,
                "due_min": 5,
                "weight": 1,
            },
        ],
        "shift": {
            "start_min": 5,
            "travel_min_per_unit": 1,
            "depot_x": 2,
            "depot_y": 1,
        },
        "observed_optima": [
            {
                "carding": {
                    "CARD-00": "MACHINE-00",
                    "CARD-01": "MACHINE-01",
                },
                "pairing": {
                    "WO-0000": "MACHINE-00",
                    "WO-0001": "MACHINE-01",
                    "WO-0002": "MACHINE-01",
                    "WO-0003": "MACHINE-00",
                },
                "route": ["WO-0000", "WO-0003", "WO-0001", "WO-0002"],
            },
            {
                "carding": {
                    "CARD-00": "MACHINE-00",
                    "CARD-01": "MACHINE-01",
                },
                "pairing": {
                    "WO-0000": "MACHINE-00",
                    "WO-0001": "MACHINE-01",
                    "WO-0002": "MACHINE-01",
                    "WO-0003": "MACHINE-00",
                },
                "route": ["WO-0000", "WO-0003", "WO-0002", "WO-0001"],
            },
        ],
    }


def _history_one() -> dict[str, object]:
    return {
        "history_id": "HIST-01",
        "machines": [
            {"machine_id": "MACHINE-00", "x": 4, "y": 3},
            {"machine_id": "MACHINE-01", "x": 0, "y": 4},
        ],
        "cards": [
            {
                "card_id": "CARD-00",
                "signature": [5, -2, 0, 2, -2, -2],
                "windows": [[0, 400], [50, 500]],
            },
            {
                "card_id": "CARD-01",
                "signature": [-1, -1, 6, 0, 1, -1],
                "windows": [[0, 400], [50, 500]],
            },
        ],
        "orders": [
            {
                "order_id": "WO-0000",
                "symptom": [5, 5, 4, 1, 3, 5],
                "duration_min": 20,
                "due_min": 45,
                "weight": 1,
            },
            {
                "order_id": "WO-0001",
                "symptom": [3, 3, 5, 0, 4, 6],
                "duration_min": 10,
                "due_min": 60,
                "weight": 3,
            },
            {
                "order_id": "WO-0002",
                "symptom": [5, 5, 0, 2, 2, 6],
                "duration_min": 20,
                "due_min": 5,
                "weight": 1,
            },
            {
                "order_id": "WO-0003",
                "symptom": [3, 0, 2, 4, 4, 0],
                "duration_min": 5,
                "due_min": 15,
                "weight": 2,
            },
        ],
        "shift": {
            "start_min": 5,
            "travel_min_per_unit": 2,
            "depot_x": 4,
            "depot_y": 2,
        },
        "observed_optima": [
            {
                "carding": {
                    "CARD-00": "MACHINE-01",
                    "CARD-01": "MACHINE-00",
                },
                "pairing": {
                    "WO-0000": "MACHINE-00",
                    "WO-0001": "MACHINE-00",
                    "WO-0002": "MACHINE-01",
                    "WO-0003": "MACHINE-01",
                },
                "route": ["WO-0001", "WO-0000", "WO-0003", "WO-0002"],
            },
            {
                "carding": {
                    "CARD-00": "MACHINE-01",
                    "CARD-01": "MACHINE-00",
                },
                "pairing": {
                    "WO-0000": "MACHINE-00",
                    "WO-0001": "MACHINE-00",
                    "WO-0002": "MACHINE-01",
                    "WO-0003": "MACHINE-01",
                },
                "route": ["WO-0003", "WO-0002", "WO-0001", "WO-0000"],
            },
        ],
    }


def _history_two() -> dict[str, object]:
    return {
        "history_id": "HIST-02",
        "machines": [
            {"machine_id": "MACHINE-00", "x": 0, "y": 3},
            {"machine_id": "MACHINE-01", "x": 5, "y": 4},
        ],
        "cards": [
            {
                "card_id": "CARD-00",
                "signature": [1, -2, 2, 3, 1, 2],
                "windows": [[0, 400], [50, 500]],
            },
            {
                "card_id": "CARD-01",
                "signature": [-1, 0, 0, 6, 6, -2],
                "windows": [[0, 400], [50, 500]],
            },
        ],
        "orders": [
            {
                "order_id": "WO-0000",
                "symptom": [0, 3, 0, 1, 5, 3],
                "duration_min": 20,
                "due_min": 60,
                "weight": 2,
            },
            {
                "order_id": "WO-0001",
                "symptom": [6, 3, 3, 3, 2, 4],
                "duration_min": 10,
                "due_min": 15,
                "weight": 3,
            },
            {
                "order_id": "WO-0002",
                "symptom": [1, 0, 0, 1, 4, 1],
                "duration_min": 5,
                "due_min": 5,
                "weight": 3,
            },
            {
                "order_id": "WO-0003",
                "symptom": [2, 5, 5, 0, 3, 3],
                "duration_min": 10,
                "due_min": 30,
                "weight": 2,
            },
        ],
        "shift": {
            "start_min": 5,
            "travel_min_per_unit": 1,
            "depot_x": 1,
            "depot_y": 1,
        },
        "observed_optima": [
            {
                "carding": {
                    "CARD-00": "MACHINE-01",
                    "CARD-01": "MACHINE-00",
                },
                "pairing": {
                    "WO-0000": "MACHINE-00",
                    "WO-0001": "MACHINE-01",
                    "WO-0002": "MACHINE-00",
                    "WO-0003": "MACHINE-01",
                },
                "route": ["WO-0002", "WO-0000", "WO-0001", "WO-0003"],
            },
            {
                "carding": {
                    "CARD-00": "MACHINE-01",
                    "CARD-01": "MACHINE-00",
                },
                "pairing": {
                    "WO-0000": "MACHINE-00",
                    "WO-0001": "MACHINE-01",
                    "WO-0002": "MACHINE-01",
                    "WO-0003": "MACHINE-00",
                },
                "route": ["WO-0002", "WO-0001", "WO-0003", "WO-0000"],
            },
        ],
    }


def _held_out() -> dict[str, object]:
    return {
        "batch_id": "BATCH-A0",
        "machines": [
            {"machine_id": "MACHINE-0A", "x": 3, "y": 6},
            {"machine_id": "MACHINE-1B", "x": 6, "y": 0},
            {"machine_id": "MACHINE-2C", "x": 4, "y": 2},
        ],
        "cards": [
            {
                "card_id": "CARD-0A",
                "signature": [6, 11, 3, 7, 10, 11],
                "windows": [[20, 170], [60, 180]],
            },
            {
                "card_id": "CARD-1B",
                "signature": [4, 6, 10, 12, 6, 9],
                "windows": [[30, 180], [60, 180]],
            },
            {
                "card_id": "CARD-2C",
                "signature": [8, 6, 12, 8, 4, 1],
                "windows": [[40, 140], [60, 180]],
            },
        ],
        "orders": [
            {
                "order_id": "WO-0100",
                "symptom": [9, 0, 9, 6, 2, 10],
                "duration_min": 15,
                "due_min": 30,
                "weight": 3,
            },
            {
                "order_id": "WO-0101",
                "symptom": [10, 2, 12, 11, 8, 4],
                "duration_min": 20,
                "due_min": 40,
                "weight": 3,
            },
            {
                "order_id": "WO-0102",
                "symptom": [8, 8, 9, 5, 1, 4],
                "duration_min": 30,
                "due_min": 60,
                "weight": 1,
            },
            {
                "order_id": "WO-0103",
                "symptom": [11, 2, 5, 12, 8, 10],
                "duration_min": 20,
                "due_min": 50,
                "weight": 3,
            },
            {
                "order_id": "WO-0104",
                "symptom": [5, 5, 1, 4, 4, 7],
                "duration_min": 10,
                "due_min": 60,
                "weight": 1,
            },
            {
                "order_id": "WO-0105",
                "symptom": [11, 4, 1, 2, 1, 6],
                "duration_min": 10,
                "due_min": 50,
                "weight": 3,
            },
        ],
        "shift": {
            "start_min": 10,
            "travel_min_per_unit": 1,
            "depot_x": 0,
            "depot_y": 8,
        },
    }


def _payload() -> dict[str, object]:
    return {
        "schema": "inverse-maint-v1",
        "histories": [_history_zero(), _history_one(), _history_two()],
        "held_out": _held_out(),
    }


def _expected_metrics() -> dict[str, int]:
    return {
        "objective": 3574,
        "skill_penalty": 957,
        "total_setup": 14,
        "total_travel": 23,
        "weighted_tardiness": 560,
    }


def _expected_pairing() -> dict[str, str]:
    return {
        "WO-0100": "MACHINE-0A",
        "WO-0101": "MACHINE-1B",
        "WO-0102": "MACHINE-0A",
        "WO-0103": "MACHINE-2C",
        "WO-0104": "MACHINE-2C",
        "WO-0105": "MACHINE-1B",
    }


def _expected_carding() -> dict[str, str]:
    return {
        "CARD-0A": "MACHINE-2C",
        "CARD-1B": "MACHINE-0A",
        "CARD-2C": "MACHINE-1B",
    }


def test_inverse_weights_are_recovered(tmp_path: Path) -> None:
    """题面：「隐藏权重是四个正整数」"""
    payload = _payload()
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    assert completed.returncode == 0, 'FAILED CASE-WEIGHT-RECOVERY-01 CASE-WEIGHT-SILENT-01 CASE-WEIGHT-UNIQUE-01 CASE-INVERSE-BASELINE-01 CASE-WEIGHT-GCD-01 CASE-WEIGHT-BOUND-01 CASE-SAFE-NO-HARDCODE-01'
    result = json.loads(output.read_text(encoding="utf-8"))
    assert completed.returncode == 0, 'FAILED CASE-WEIGHT-RECOVERY-01 CASE-WEIGHT-SILENT-01 CASE-WEIGHT-UNIQUE-01 CASE-INVERSE-BASELINE-01 CASE-WEIGHT-GCD-01 CASE-WEIGHT-BOUND-01 CASE-SAFE-NO-HARDCODE-01'
    assert completed.stdout == "", "FAILED CASE-WEIGHT-SILENT-01"
    assert completed.stderr == "", "FAILED CASE-WEIGHT-SILENT-01"
    assert result["weights"] == {
        "skill": 3,
        "setup": 2,
        "travel": 5,
        "tardiness": 1,
    }, "FAILED CASE-WEIGHT-RECOVERY-01"
    assert result["certificate"]["equality_rank"] == 3, (
        "FAILED CASE-WEIGHT-UNIQUE-01"
    )
    _record_pass(
        "FAILED CASE-INVERSE-BASELINE-01",
        "FAILED CASE-WEIGHT-RECOVERY-01",
        "FAILED CASE-WEIGHT-SILENT-01",
        "FAILED CASE-WEIGHT-UNIQUE-01",
        "FAILED CASE-WEIGHT-GCD-01",
        "FAILED CASE-WEIGHT-BOUND-01",
        "FAILED CASE-SAFE-NO-HARDCODE-01",
    )


def test_certificate_margins_are_exact(tmp_path: Path) -> None:
    """题面：「后者按输入历史顺序给出每份历史中」"""
    payload = _payload()
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    assert completed.returncode == 0, 'FAILED CASE-MARGIN-01 CASE-CERTIFICATE-FIELDS-01 CASE-MARGIN-ORDER-01 CASE-WEIGHT-FIELDS-01'
    result = json.loads(output.read_text(encoding="utf-8"))
    assert completed.returncode == 0, 'FAILED CASE-MARGIN-01 CASE-CERTIFICATE-FIELDS-01 CASE-MARGIN-ORDER-01 CASE-WEIGHT-FIELDS-01'
    assert result["certificate"] == {
        "equality_rank": 3,
        "margins": [32, 10, 2],
    }, "FAILED CASE-MARGIN-01 CASE-CERTIFICATE-FIELDS-01"
    assert set(result["certificate"]) == {
        "equality_rank",
        "margins",
    }, "FAILED CASE-CERTIFICATE-FIELDS-01"
    _record_pass(
        "FAILED CASE-MARGIN-01",
        "FAILED CASE-CERTIFICATE-FIELDS-01",
        "FAILED CASE-MARGIN-ORDER-01",
        "FAILED CASE-WEIGHT-FIELDS-01",
    )


def test_held_out_plan_uses_recovered_weights(tmp_path: Path) -> None:
    """题面：「`plan` 取 `held_out` 中主目标最小的方案。」"""
    payload = _payload()
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    assert completed.returncode == 0, 'FAILED CASE-HELD-PLAN-01 CASE-CARDING-MAP-01 CASE-PAIRING-MAP-01 CASE-ROUTE-PLAN-01 CASE-OUTPUT-PLAN-01'
    result = json.loads(output.read_text(encoding="utf-8"))
    assert completed.returncode == 0, 'FAILED CASE-HELD-PLAN-01 CASE-CARDING-MAP-01 CASE-PAIRING-MAP-01 CASE-ROUTE-PLAN-01 CASE-OUTPUT-PLAN-01'
    assert result["plan"]["carding"] == _expected_carding(), (
        "FAILED CASE-HELD-PLAN-01 CASE-CARDING-MAP-01"
    )
    assert result["plan"]["pairing"] == _expected_pairing(), (
        "FAILED CASE-HELD-PLAN-01 CASE-PAIRING-MAP-01"
    )
    assert result["plan"]["route"] == [
        "WO-0103",
        "WO-0104",
        "WO-0105",
        "WO-0101",
        "WO-0100",
        "WO-0102",
    ], "FAILED CASE-HELD-PLAN-01 CASE-ROUTE-PLAN-01"
    _record_pass(
        "FAILED CASE-HELD-PLAN-01",
        "FAILED CASE-CARDING-MAP-01",
        "FAILED CASE-PAIRING-MAP-01",
        "FAILED CASE-ROUTE-PLAN-01",
        "FAILED CASE-OUTPUT-PLAN-01",
    )


def test_held_out_metrics_follow_weighted_components(tmp_path: Path) -> None:
    """题面：「`objective` 是前四项按恢复权重加权后的和。」"""
    payload = _payload()
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    assert completed.returncode == 0, 'FAILED CASE-METRICS-01 CASE-METRICS-FIELDS-01 CASE-OBJECTIVE-DOT-01 CASE-COST-COMPONENTS-01 CASE-SETUP-COST-01 CASE-TRAVEL-COST-01 CASE-TARDINESS-COST-01'
    result = json.loads(output.read_text(encoding="utf-8"))
    metrics = result["plan"]["metrics"]
    weights = result["weights"]
    assert completed.returncode == 0, 'FAILED CASE-METRICS-01 CASE-METRICS-FIELDS-01 CASE-OBJECTIVE-DOT-01 CASE-COST-COMPONENTS-01 CASE-SETUP-COST-01 CASE-TRAVEL-COST-01 CASE-TARDINESS-COST-01'
    assert metrics == _expected_metrics(), (
        "FAILED CASE-METRICS-01 CASE-METRICS-FIELDS-01"
    )
    assert (
        weights["skill"] * metrics["skill_penalty"]
        + weights["setup"] * metrics["total_setup"]
        + weights["travel"] * metrics["total_travel"]
        + weights["tardiness"] * metrics["weighted_tardiness"]
        == metrics["objective"]
    ), "FAILED CASE-OBJECTIVE-DOT-01"
    assert set(metrics) == {
        "objective",
        "skill_penalty",
        "total_setup",
        "total_travel",
        "weighted_tardiness",
    }, "FAILED CASE-METRICS-FIELDS-01"
    _record_pass(
        "FAILED CASE-METRICS-01",
        "FAILED CASE-METRICS-FIELDS-01",
        "FAILED CASE-OBJECTIVE-DOT-01",
        "FAILED CASE-COST-COMPONENTS-01",
        "FAILED CASE-SETUP-COST-01",
        "FAILED CASE-TRAVEL-COST-01",
        "FAILED CASE-TARDINESS-COST-01",
    )


def test_held_out_route_has_contiguous_blocks(tmp_path: Path) -> None:
    """题面：「路线中的相邻两张必须属于同一设备块」"""
    payload = _payload()
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    assert completed.returncode == 0, 'FAILED CASE-ROUTE-CONTIG-01 CASE-ROUTE-COVER-01 CASE-ROUTE-BLOCK-ONCE-01'
    result = json.loads(output.read_text(encoding="utf-8"))
    route_machines = [
        result["plan"]["pairing"][order_id]
        for order_id in result["plan"]["route"]
    ]
    assert completed.returncode == 0, 'FAILED CASE-ROUTE-CONTIG-01 CASE-ROUTE-COVER-01 CASE-ROUTE-BLOCK-ONCE-01'
    assert route_machines[0::2] == route_machines[1::2], (
        "FAILED CASE-ROUTE-CONTIG-01"
    )
    assert len(set(route_machines[0::2])) == 3, "FAILED CASE-ROUTE-COVER-01"
    _record_pass(
        "FAILED CASE-ROUTE-CONTIG-01",
        "FAILED CASE-ROUTE-COVER-01",
        "FAILED CASE-ROUTE-BLOCK-ONCE-01",
    )


def test_held_out_canonical_tie_break(tmp_path: Path) -> None:
    """题面：「先比较 `route` 的工单号序列」"""
    payload = _payload()
    held = payload["held_out"]
    for machine in held["machines"]:
        machine["x"] = 0
        machine["y"] = 0
    for card in held["cards"]:
        card["signature"] = [0, 0, 0, 0, 0, 0]
        card["windows"] = [[0, 400], [50, 500]]
    for order in held["orders"]:
        order["symptom"] = [0, 0, 0, 0, 0, 0]
        order["duration_min"] = 1
        order["due_min"] = 1000
        order["weight"] = 1
    held["shift"] = {
        "start_min": 0,
        "travel_min_per_unit": 1,
        "depot_x": 0,
        "depot_y": 0,
    }
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    assert completed.returncode == 0, 'FAILED CASE-TIE-ROUTE-01 CASE-TIE-CARD-01 CASE-TIE-MACHINE-01 CASE-TIE-LEX-01'
    result = json.loads(output.read_text(encoding="utf-8"))
    assert completed.returncode == 0, 'FAILED CASE-TIE-ROUTE-01 CASE-TIE-CARD-01 CASE-TIE-MACHINE-01 CASE-TIE-LEX-01'
    assert result["plan"]["route"] == [
        "WO-0100",
        "WO-0101",
        "WO-0102",
        "WO-0103",
        "WO-0104",
        "WO-0105",
    ], "FAILED CASE-TIE-ROUTE-01"
    assert result["plan"]["carding"] == {
        "CARD-0A": "MACHINE-0A",
        "CARD-1B": "MACHINE-1B",
        "CARD-2C": "MACHINE-2C",
    }, "FAILED CASE-TIE-CARD-01 CASE-TIE-MACHINE-01"
    _record_pass(
        "FAILED CASE-TIE-ROUTE-01",
        "FAILED CASE-TIE-CARD-01",
        "FAILED CASE-TIE-MACHINE-01",
        "FAILED CASE-TIE-LEX-01",
    )


def test_later_window_is_used_when_first_is_too_short(tmp_path: Path) -> None:
    """题面：「若较早窗口容不下而较晚窗口可以完成，则使用较晚窗口。」"""
    payload = _payload()
    held = payload["held_out"]
    for machine in held["machines"]:
        machine["x"] = 0
        machine["y"] = 0
    for card in held["cards"]:
        card["signature"] = [0, 0, 0, 0, 0, 0]
        card["windows"] = [[0, 1], [0, 500]]
    for order in held["orders"]:
        order["symptom"] = [0, 0, 0, 0, 0, 0]
        order["duration_min"] = 1
        order["due_min"] = 1000
        order["weight"] = 1
    held["shift"] = {
        "start_min": 0,
        "travel_min_per_unit": 1,
        "depot_x": 0,
        "depot_y": 0,
    }
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    assert completed.returncode == 0, 'FAILED CASE-WINDOW-FALLBACK-01 CASE-WINDOW-START-01 CASE-WINDOW-SELECT-01'
    result = json.loads(output.read_text(encoding="utf-8"))
    assert completed.returncode == 0, 'FAILED CASE-WINDOW-FALLBACK-01 CASE-WINDOW-START-01 CASE-WINDOW-SELECT-01'
    assert result["plan"]["metrics"]["objective"] == 8, (
        "FAILED CASE-WINDOW-FALLBACK-01"
    )
    _record_pass(
        "FAILED CASE-WINDOW-FALLBACK-01",
        "FAILED CASE-WINDOW-START-01",
        "FAILED CASE-WINDOW-SELECT-01",
    )


def test_touching_windows_are_refused(tmp_path: Path) -> None:
    """题面：「同一张卡片的窗口区间不得重叠，首尾相接也不算合法。」"""
    payload = _payload()
    held = payload["held_out"]
    for machine in held["machines"]:
        machine["x"] = 0
        machine["y"] = 0
    for card in held["cards"]:
        card["signature"] = [0, 0, 0, 0, 0, 0]
        card["windows"] = [[0, 10], [10, 20]]
    for order in held["orders"]:
        order["symptom"] = [0, 0, 0, 0, 0, 0]
        order["duration_min"] = 1
        order["due_min"] = 0
        order["weight"] = 1
    held["shift"] = {
        "start_min": 0,
        "travel_min_per_unit": 1,
        "depot_x": 0,
        "depot_y": 0,
    }
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    assert completed.returncode == 2
    assert completed.stderr.startswith("REFUSED: ")
    assert not output.exists()


def test_block_finishing_at_window_close_is_accepted(tmp_path: Path) -> None:
    """题面：「块的开工时刻取能完成它的」"""
    payload = _payload()
    held = payload["held_out"]
    for machine in held["machines"]:
        machine["x"] = 0
        machine["y"] = 0
    for card in held["cards"]:
        card["signature"] = [0, 0, 0, 0, 0, 0]
        card["windows"] = [[0, 10], [9, 500]]
    for order in held["orders"]:
        order["symptom"] = [0, 0, 0, 0, 0, 0]
        order["duration_min"] = 1
        order["due_min"] = 0
        order["weight"] = 1
    held["shift"] = {
        "start_min": 0,
        "travel_min_per_unit": 1,
        "depot_x": 0,
        "depot_y": 0,
    }
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    result = json.loads(output.read_text(encoding="utf-8"))
    assert completed.returncode == 0
    assert result["plan"]["metrics"]["total_setup"] == 4
    assert result["plan"]["metrics"]["weighted_tardiness"] == 33


def test_success_output_is_compact_sorted_and_newline_terminated(
    tmp_path: Path,
) -> None:
    """题面：「同一份历史与 held-out 包重跑时，应重建相同证书和路线字节。」"""
    payload = _payload()
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    second_output = tmp_path / "result-copy.json"
    _write_json(source, payload)
    completed = _run(source, output)
    second_run = _run(source, second_output)
    assert completed.returncode == 0, 'FAILED CASE-SERIAL-01 CASE-OUTPUT-FIELDS-01 CASE-OUTPUT-WEIGHTS-01 CASE-OUTPUT-CERTIFICATE-01'
    raw = output.read_bytes()
    assert second_run.returncode == 0
    assert completed.returncode == 0, 'FAILED CASE-SERIAL-01 CASE-OUTPUT-FIELDS-01 CASE-OUTPUT-WEIGHTS-01 CASE-OUTPUT-CERTIFICATE-01'
    parsed = json.loads(raw)
    canonical = (
        json.dumps(parsed, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    )
    assert completed.returncode == 0, 'FAILED CASE-SERIAL-01 CASE-OUTPUT-FIELDS-01 CASE-OUTPUT-WEIGHTS-01 CASE-OUTPUT-CERTIFICATE-01'
    assert raw == canonical, "FAILED CASE-SERIAL-01"
    assert second_output.read_bytes() == raw, "FAILED CASE-SERIAL-01"
    assert set(parsed) == {
        "certificate",
        "plan",
        "status",
        "weights",
    }, "FAILED CASE-OUTPUT-FIELDS-01"
    _record_pass(
        "FAILED CASE-SERIAL-01",
        "FAILED CASE-OUTPUT-FIELDS-01",
        "FAILED CASE-OUTPUT-WEIGHTS-01",
        "FAILED CASE-OUTPUT-CERTIFICATE-01",
    )


def test_extra_top_level_key_is_refused(tmp_path: Path) -> None:
    """题面：「输入顶层只能有 `schema`、`histories`、`held_out`。」"""
    payload = _payload()
    payload["planner"] = "legacy"
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    assert completed.returncode == 2, 'FAILED CASE-TOP-KEYS-01 CASE-REFUSAL-NO-FILE-01 CASE-TOP-SECTIONS-01 CASE-REFUSAL-PREFIX-01'
    assert completed.stdout == "", "FAILED CASE-TOP-KEYS-01"
    assert completed.stderr.startswith("REFUSED: "), "FAILED CASE-TOP-KEYS-01"
    assert not output.exists(), "FAILED CASE-REFUSAL-NO-FILE-01"
    _record_pass(
        "FAILED CASE-TOP-KEYS-01",
        "FAILED CASE-TOP-SECTIONS-01",
        "FAILED CASE-REFUSAL-NO-FILE-01",
        "FAILED CASE-REFUSAL-PREFIX-01",
    )


def test_wrong_schema_is_refused(tmp_path: Path) -> None:
    """题面：「`schema` 固定为」"""
    payload = _payload()
    payload["schema"] = "maint-plan-v3"
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    assert completed.returncode == 2, 'FAILED CASE-SCHEMA-01'
    assert completed.stderr.startswith("REFUSED: "), "FAILED CASE-SCHEMA-01"
    assert not output.exists(), "FAILED CASE-SCHEMA-01"
    _record_pass("FAILED CASE-SCHEMA-01")


def test_wrong_history_count_is_refused(tmp_path: Path) -> None:
    """题面：「`histories` 固定放 3 份记录。」"""
    payload = _payload()
    payload["histories"].pop()
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    assert completed.returncode == 2, 'FAILED CASE-HISTORY-COUNT-01'
    assert completed.stderr.startswith("REFUSED: "), (
        "FAILED CASE-HISTORY-COUNT-01"
    )
    assert not output.exists(), "FAILED CASE-HISTORY-COUNT-01"
    _record_pass("FAILED CASE-HISTORY-COUNT-01")


def test_non_overlapping_windows_are_refused(tmp_path: Path) -> None:
    """题面：「两段窗口满足 `max(open_min) < min(close_min)`。」"""
    payload = _payload()
    payload["held_out"]["cards"][0]["windows"] = [[0, 10], [20, 40]]
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    assert completed.returncode == 2, 'FAILED CASE-WINDOW-OVERLAP-01'
    assert completed.stderr.startswith("REFUSED: "), (
        "FAILED CASE-WINDOW-OVERLAP-01"
    )
    assert not output.exists(), "FAILED CASE-WINDOW-OVERLAP-01"
    _record_pass("FAILED CASE-WINDOW-OVERLAP-01")


def test_boolean_window_timestamp_is_refused(tmp_path: Path) -> None:
    """题面：「四个时刻都是非负整数」"""
    payload = _payload()
    payload["held_out"]["cards"][0]["windows"][0][0] = True
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    assert completed.returncode == 2, 'FAILED CASE-WINDOW-INT-01'
    assert completed.stderr.startswith("REFUSED: "), "FAILED CASE-WINDOW-INT-01"
    assert not output.exists(), "FAILED CASE-WINDOW-INT-01"
    _record_pass("FAILED CASE-WINDOW-INT-01")


def test_short_signature_is_refused(tmp_path: Path) -> None:
    """题面：「`signature` 是 6 个整数。」"""
    payload = _payload()
    payload["held_out"]["cards"][0]["signature"].pop()
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    assert completed.returncode == 2, 'FAILED CASE-SIGNATURE-LEN-01'
    assert completed.stderr.startswith("REFUSED: "), (
        "FAILED CASE-SIGNATURE-LEN-01"
    )
    assert not output.exists(), "FAILED CASE-SIGNATURE-LEN-01"
    _record_pass("FAILED CASE-SIGNATURE-LEN-01")


def test_wrong_observed_count_is_refused(tmp_path: Path) -> None:
    """题面：「`observed_optima` 恰好包含 2 个方案对象」"""
    payload = _payload()
    payload["histories"][0]["observed_optima"].pop()
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    assert completed.returncode == 2, 'FAILED CASE-OBSERVED-COUNT-01 CASE-OBSERVED-PLAN-FIELDS-01'
    assert completed.stderr.startswith("REFUSED: "), (
        "FAILED CASE-OBSERVED-COUNT-01"
    )
    assert not output.exists(), "FAILED CASE-OBSERVED-COUNT-01"
    _record_pass(
        "FAILED CASE-OBSERVED-COUNT-01",
        "FAILED CASE-OBSERVED-PLAN-FIELDS-01",
    )


def test_observed_optima_must_include_all_ties(tmp_path: Path) -> None:
    """题面：「它们是在本份历史记录的全部可行方案中」"""
    payload = _payload()
    payload["histories"][0]["observed_optima"][1]["route"] = [
        "WO-0001",
        "WO-0002",
        "WO-0000",
        "WO-0003",
    ]
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    assert completed.returncode == 2, 'FAILED CASE-OPTIMAL-FACE-01'
    assert completed.stderr.startswith("REFUSED: "), (
        "FAILED CASE-OPTIMAL-FACE-01"
    )
    assert not output.exists(), "FAILED CASE-OPTIMAL-FACE-01"
    _record_pass("FAILED CASE-OPTIMAL-FACE-01")


def test_rank_deficient_history_ties_are_refused(tmp_path: Path) -> None:
    """题面：「四维成本差向量必须线性无关，秩恰为 3。」"""
    payload = _payload()
    base = copy.deepcopy(payload["histories"][0])
    payload["histories"][1] = copy.deepcopy(base)
    payload["histories"][1]["history_id"] = "HIST-01"
    payload["histories"][2] = copy.deepcopy(base)
    payload["histories"][2]["history_id"] = "HIST-02"
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    assert completed.returncode == 2, 'FAILED CASE-RANK-01 CASE-WEIGHT-PRIMITIVE-01 CASE-WEIGHT-RAY-01'
    assert completed.stderr.startswith("REFUSED: "), "FAILED CASE-RANK-01"
    assert not output.exists(), "FAILED CASE-RANK-01"
    _record_pass(
        "FAILED CASE-RANK-01",
        "FAILED CASE-WEIGHT-PRIMITIVE-01",
        "FAILED CASE-WEIGHT-RAY-01",
    )


def test_gate_success_has_exact_top_keys(tmp_path: Path) -> None:
    """题面：「成功结果只保留 `status`、`weights`、`certificate`、`plan` 四项。」"""
    payload = _payload()
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    assert completed.returncode == 0, 'FAILED CASE-GATE-SUCCESS-01'
    result = json.loads(output.read_text(encoding="utf-8"))
    assert completed.returncode == 0, 'FAILED CASE-GATE-SUCCESS-01'
    assert set(result) == {
        "certificate",
        "plan",
        "status",
        "weights",
    }, "FAILED CASE-GATE-SUCCESS-01"
    assert result["status"] == "ok", "FAILED CASE-GATE-SUCCESS-01"
    _record_pass("FAILED CASE-GATE-SUCCESS-01")


def test_gate_nested_packages_match_declared_shapes(tmp_path: Path) -> None:
    """题面：「每份只能有 `history_id`、`machines`、`cards`、`orders`、」"""
    payload = _payload()
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    histories = payload["histories"]
    held = payload["held_out"]
    machines = [
        machine
        for package in [*histories, held]
        for machine in package["machines"]
    ]
    cards = [
        card for package in [*histories, held] for card in package["cards"]
    ]
    orders = [
        order for package in [*histories, held] for order in package["orders"]
    ]
    assert completed.returncode == 0, 'FAILED CASE-HISTORY-FIELDS-01 CASE-HELD-FIELDS-01 CASE-MACHINE-FIELDS-01 CASE-CARD-FIELDS-01 CASE-ORDER-FIELDS-01 CASE-SHIFT-FIELDS-01 CASE-HISTORY-ID-01 CASE-BATCH-ID-01 CASE-MACHINE-ID-01 CASE-CARD-ID-01 CASE-ORDER-ID-01 CASE-SIGNATURE-LEN-01 CASE-WINDOW-COUNT-01 CASE-SYMPTOM-LEN-01 CASE-DURATION-POS-01 CASE-WEIGHT-POS-01 CASE-DUE-DOMAIN-01 CASE-COORD-DOMAIN-01 CASE-TRAVEL-DOMAIN-01 CASE-MACHINE-XY-01 CASE-CARD-WINDOWS-01'
    assert all(
        set(history)
        == {
            "history_id",
            "machines",
            "cards",
            "orders",
            "shift",
            "observed_optima",
        }
        for history in histories
    ), "FAILED CASE-HISTORY-FIELDS-01"
    assert set(held) == {
        "batch_id",
        "machines",
        "cards",
        "orders",
        "shift",
    }, "FAILED CASE-HELD-FIELDS-01"
    assert all(
        set(machine) == {"machine_id", "x", "y"} for machine in machines
    ), "FAILED CASE-MACHINE-FIELDS-01"
    assert all(
        set(card) == {"card_id", "signature", "windows"} for card in cards
    ), "FAILED CASE-CARD-FIELDS-01"
    assert all(
        set(order)
        == {"order_id", "symptom", "duration_min", "due_min", "weight"}
        for order in orders
    ), "FAILED CASE-ORDER-FIELDS-01"
    assert all(
        set(package["shift"])
        == {"start_min", "travel_min_per_unit", "depot_x", "depot_y"}
        for package in [*histories, held]
    ), "FAILED CASE-SHIFT-FIELDS-01"
    assert all(
        re.fullmatch(r"HIST-[0-9]{2}", history["history_id"])
        for history in histories
    ), "FAILED CASE-HISTORY-ID-01"
    assert re.fullmatch(r"BATCH-[A-Z0-9]{2}", held["batch_id"]), (
        "FAILED CASE-BATCH-ID-01"
    )
    assert all(
        re.fullmatch(r"MACHINE-[A-Z0-9]{2}", machine["machine_id"])
        for machine in machines
    ), "FAILED CASE-MACHINE-ID-01"
    assert all(
        re.fullmatch(r"CARD-[A-Z0-9]{2}", card["card_id"]) for card in cards
    ), "FAILED CASE-CARD-ID-01"
    assert all(
        re.fullmatch(r"WO-[A-Z0-9]{4}", order["order_id"]) for order in orders
    ), "FAILED CASE-ORDER-ID-01"
    assert all(
        len(card["signature"]) == 6
        and len(card["windows"]) == 2
        and all(len(window) == 2 for window in card["windows"])
        for card in cards
    ), "FAILED CASE-SIGNATURE-LEN-01 CASE-WINDOW-COUNT-01"
    assert all(
        len(order["symptom"]) == 6
        and order["duration_min"] > 0
        and order["weight"] > 0
        and order["due_min"] >= 0
        for order in orders
    ), (
        "FAILED CASE-SYMPTOM-LEN-01 CASE-DURATION-POS-01 "
        "FAILED CASE-WEIGHT-POS-01 CASE-DUE-DOMAIN-01"
    )
    assert all(
        machine["x"] >= 0
        and machine["y"] >= 0
        and package["shift"]["travel_min_per_unit"] >= 1
        for package in [*histories, held]
        for machine in package["machines"]
    ), "FAILED CASE-COORD-DOMAIN-01 CASE-TRAVEL-DOMAIN-01"
    _record_pass(
        "FAILED CASE-HISTORY-FIELDS-01",
        "FAILED CASE-HELD-FIELDS-01",
        "FAILED CASE-MACHINE-FIELDS-01",
        "FAILED CASE-MACHINE-XY-01",
        "FAILED CASE-CARD-FIELDS-01",
        "FAILED CASE-CARD-WINDOWS-01",
        "FAILED CASE-ORDER-FIELDS-01",
        "FAILED CASE-SHIFT-FIELDS-01",
        "FAILED CASE-HISTORY-ID-01",
        "FAILED CASE-BATCH-ID-01",
        "FAILED CASE-MACHINE-ID-01",
        "FAILED CASE-CARD-ID-01",
        "FAILED CASE-ORDER-ID-01",
        "FAILED CASE-SIGNATURE-LEN-01",
        "FAILED CASE-WINDOW-COUNT-01",
        "FAILED CASE-SYMPTOM-LEN-01",
        "FAILED CASE-DURATION-POS-01",
        "FAILED CASE-WEIGHT-POS-01",
        "FAILED CASE-DUE-DOMAIN-01",
        "FAILED CASE-COORD-DOMAIN-01",
        "FAILED CASE-TRAVEL-DOMAIN-01",
    )


def test_gate_observed_suboptimal_is_refused(tmp_path: Path) -> None:
    """题面：「也不能夹入次优方案。」"""
    payload = _payload()
    payload["histories"][0]["observed_optima"][1]["route"] = [
        "WO-0001",
        "WO-0002",
        "WO-0000",
        "WO-0003",
    ]
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    assert completed.returncode == 2, 'FAILED CASE-GATE-SUBOPTIMAL-01'
    assert completed.stdout == "", "FAILED CASE-GATE-SUBOPTIMAL-01"
    assert not output.exists(), "FAILED CASE-GATE-SUBOPTIMAL-01"
    _record_pass("FAILED CASE-GATE-SUBOPTIMAL-01")


def test_gate_invalid_carding_is_refused(tmp_path: Path) -> None:
    """题面：「一份方案由三张卡片到设备的双射」"""
    payload = _payload()
    payload["histories"][0]["observed_optima"][0]["carding"] = {
        "CARD-00": "MACHINE-00",
        "CARD-01": "MACHINE-00",
    }
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    assert completed.returncode == 2, 'FAILED CASE-GATE-CARDING-01 CASE-CARDING-BIJECTION-01 CASE-PAIRING-CAPACITY-01'
    assert completed.stderr.startswith("REFUSED: "), (
        "FAILED CASE-GATE-CARDING-01"
    )
    assert not output.exists(), "FAILED CASE-GATE-CARDING-01"
    _record_pass(
        "FAILED CASE-GATE-CARDING-01",
        "FAILED CASE-CARDING-BIJECTION-01",
        "FAILED CASE-PAIRING-CAPACITY-01",
    )


def test_gate_split_route_is_refused(tmp_path: Path) -> None:
    """题面：「每个设备块在路线中出现一次」"""
    payload = _payload()
    payload["histories"][0]["observed_optima"][0]["route"] = [
        "WO-0000",
        "WO-0001",
        "WO-0002",
        "WO-0003",
    ]
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    assert completed.returncode == 2, 'FAILED CASE-GATE-ROUTE-01 CASE-ROUTE-SPLIT-01'
    assert completed.stderr.startswith("REFUSED: "), "FAILED CASE-GATE-ROUTE-01"
    assert not output.exists(), "FAILED CASE-GATE-ROUTE-01"
    _record_pass("FAILED CASE-GATE-ROUTE-01", "FAILED CASE-ROUTE-SPLIT-01")


def test_gate_duplicate_json_key_is_refused(tmp_path: Path) -> None:
    """题面：「任一 JSON 对象出现重复键都按输入不合格处理。」"""
    payload = _payload()
    raw = json.dumps(payload).replace(
        '"schema": "inverse-maint-v1"',
        '"schema": "inverse-maint-v1", "schema": "inverse-maint-v1"',
        1,
    )
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    source.write_text(raw, encoding="utf-8")
    completed = _run(source, output)
    assert completed.returncode == 2, 'FAILED CASE-DUPLICATE-JSON-01'
    assert completed.stderr.startswith("REFUSED: "), (
        "FAILED CASE-DUPLICATE-JSON-01"
    )
    assert not output.exists(), "FAILED CASE-DUPLICATE-JSON-01"
    _record_pass("FAILED CASE-DUPLICATE-JSON-01")


def test_gate_unwritable_output_is_refused(tmp_path: Path) -> None:
    """题面：「目标路径无法写入时也按同样方式」"""
    payload = _payload()
    source = tmp_path / "input.json"
    output = tmp_path / "result.json"
    output.mkdir()
    _write_json(source, payload)
    completed = _run(source, output)
    assert completed.returncode == 2, 'FAILED CASE-WRITE-FAIL-01'
    assert completed.stdout == "", "FAILED CASE-WRITE-FAIL-01"
    assert completed.stderr.startswith("REFUSED: "), "FAILED CASE-WRITE-FAIL-01"
    _record_pass("FAILED CASE-WRITE-FAIL-01")
