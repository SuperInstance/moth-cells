"""Receipted walks: HUNT/v1 header + FINDING/v1 + REFUSAL/v1 chained rows.

Row kinds match the moth-ledger family envelopes. FINDING rows carry
genome_hash + dice_seed (moth-ledger v2 proposal — canonical binds every
field present, so the chain law holds for superset rows already).
"""
from __future__ import annotations

from .model import Genome
from .terrain import terrain_hash
from .vendor_canonical import canonical_dumps
from .vendor_hashes import fnv1a_64_hex

GENESIS = "0" * 16


def _digest(row: dict) -> str:
    return fnv1a_64_hex(canonical_dumps(row))


def hunt_header(hunter, cells: list[dict], ticks: int) -> dict:
    return {
        "kind": "HUNT/v1",
        "schema_version": "1.0",
        "producer": {"tool": "moth-cells", "version": "0.1.0"},
        "terrain_hash": terrain_hash(cells),
        "genome_hash": hunter.genome.genome_id,
        "dice_seed": hunter.genome.seed,
        "start_pos": hunter.pos,
        "ticks": ticks,
    }


def finding_row(claim: dict, hunter, tick: int) -> dict:
    return {
        "kind": "FINDING/v1",
        "file": claim["file"],
        "fn": claim["fn"],
        "taint_path": [claim["cell_id"]],
        "evidence": fnv1a_64_hex(canonical_dumps(claim)),
        "genome_hash": hunter.genome.genome_id,
        "dice_seed": hunter.genome.seed,
        "tick": tick,
    }


def refusal_row(event: dict, hunter, tick: int) -> dict:
    row = {
        "kind": "REFUSAL/v1",
        "reason": event.get("reason") or event.get("type", "unknown"),
        "genome_hash": hunter.genome.genome_id,
        "dice_seed": hunter.genome.seed,
        "tick": tick,
    }
    if "cell_id" in event:
        row["cell_id"] = event["cell_id"]
    if event.get("polarity"):
        row["polarity"] = event["polarity"]
    return row


def chain(rows: list[dict]) -> list[dict]:
    out, prev = [], GENESIS
    for row in rows:
        r = dict(row)
        rh, ch = _digest(r), None
        ch = fnv1a_64_hex(bytes.fromhex(prev) + bytes.fromhex(rh))
        r["row_hash"], r["chain_hash"] = rh, ch
        out.append(r)
        prev = ch
    return out


def verify(rows: list[dict]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    prev = GENESIS
    for idx, row in enumerate(rows):
        try:
            rh, ch = row.pop("row_hash"), row.pop("chain_hash")
        except KeyError as exc:
            errors.append(f"row {idx}: missing {exc}")
            break
        if rh != _digest(row):
            errors.append(f"row {idx}: row_hash mismatch")
        if ch != fnv1a_64_hex(bytes.fromhex(prev) + bytes.fromhex(rh)):
            errors.append(f"row {idx}: chain_hash mismatch")
        prev = ch
    return (not errors), errors
