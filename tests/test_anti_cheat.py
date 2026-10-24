from __future__ import annotations

import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
from test_outputs import ENTRY, _payload, _run, _write_json  # noqa: E402


RENAMES = {
    "BATCH-A0": "BATCH-Z9",
    "HIST-00": "HIST-70",
    "HIST-01": "HIST-71",
    "HIST-02": "HIST-72",
    "MACHINE-00": "MACHINE-70",
    "MACHINE-01": "MACHINE-71",
    "MACHINE-0A": "MACHINE-7A",
    "MACHINE-1B": "MACHINE-8B",
    "MACHINE-2C": "MACHINE-9C",
    "CARD-00": "CARD-70",
    "CARD-01": "CARD-71",
    "CARD-0A": "CARD-7A",
    "CARD-1B": "CARD-8B",
    "CARD-2C": "CARD-9C",
    "WO-0000": "WO-7000",
    "WO-0001": "WO-7001",
    "WO-0002": "WO-7002",
    "WO-0003": "WO-7003",
    "WO-0100": "WO-7100",
    "WO-0101": "WO-7101",
    "WO-0102": "WO-7102",
    "WO-0103": "WO-7103",
    "WO-0104": "WO-7104",
    "WO-0105": "WO-7105",
}


def _rename(payload: dict[str, object]) -> dict[str, object]:
    encoded = json.dumps(payload, ensure_ascii=False)
    for old, new in RENAMES.items():
        encoded = encoded.replace(old, new)
    return json.loads(encoded)


def _solve(tmp_path: Path, label: str, payload: dict[str, object]) -> dict[str, object]:
    source = tmp_path / f"{label}.json"
    output = tmp_path / f"{label}-result.json"
    _write_json(source, payload)
    completed = _run(source, output)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == ""
    assert completed.stderr == ""
    return json.loads(output.read_text(encoding="utf-8"))


def test_renamed_inverse_batch_requires_computation_not_fixture_lookup(
    tmp_path: Path,
) -> None:
    original_payload = _payload()
    renamed_payload = _rename(original_payload)

    original = _solve(tmp_path, "original", original_payload)
    renamed = _solve(tmp_path, "renamed", renamed_payload)

    assert renamed["weights"] == original["weights"]
    assert renamed["certificate"] == original["certificate"]
    assert renamed["plan"]["metrics"] == original["plan"]["metrics"]
    assert renamed["plan"]["carding"] == {
        RENAMES[key]: RENAMES[value]
        for key, value in original["plan"]["carding"].items()
    }
    assert renamed["plan"]["pairing"] == {
        RENAMES[key]: RENAMES[value]
        for key, value in original["plan"]["pairing"].items()
    }
    assert renamed["plan"]["route"] == [
        RENAMES[order_id] for order_id in original["plan"]["route"]
    ]
    assert renamed != original

