"""Terrain: the CorpusIndex lattice hunters walk.

Terrain is a list of cells. Each cell: {cell_id, file, fn, taint_q16, entry_q16,
decoy (bool), sink_verified_safe (bool), neighbors (sorted cell indices)}.
Built from a moth_corpus CanonicalCorpus (canonical JSONL rows) or a plain dict
list — moth-cells does not import moth-corpus; it consumes its receipts.
"""
from __future__ import annotations

import json

from .model import Q16_DENOM
from .vendor_canonical import canonical_dumps
from .vendor_hashes import fnv1a_64_hex


def from_corpus_rows(rows: list[dict]) -> list[dict]:
    """CorpusIndex.canonical rows -> terrain cells with adjacency.

    Adjacency: cells in the same file are chained in index order; the first
    cell of each file links to the first cell of the next file (file-row
    adjacency). Import-graph adjacency lands when corpus adapters surface it.
    """
    cells = []
    for i, r in enumerate(rows):
        surf = r["surface"]
        cells.append({
            "cell_id": f'{r["file_path"]}:{surf["name"]}',
            "file": r["file_path"],
            "fn": surf["name"],
            "taint_q16": surf["taint_marks"],
            "entry_q16": surf["entry_points"],
            "decoy": bool(surf.get("decoy", False)),
            "sink_verified_safe": bool(surf.get("sink_verified_safe", False)),
            "neighbors": [],
            "_file_seq": i,
        })
    by_file: dict[str, list[int]] = {}
    for i, c in enumerate(cells):
        by_file.setdefault(c["file"], []).append(i)
    file_order = sorted(by_file, key=lambda f: by_file[f][0])
    for f in file_order:
        idxs = by_file[f]
        for j, i in enumerate(idxs):
            if j + 1 < len(idxs):
                cells[i]["neighbors"].append(idxs[j + 1])
            if j > 0:
                cells[i]["neighbors"].append(idxs[j - 1])
    for k in range(len(file_order) - 1):
        a = by_file[file_order[k]][-1]
        b = by_file[file_order[k + 1]][0]
        cells[a]["neighbors"].append(b)
        cells[b]["neighbors"].append(a)
    for c in cells:
        c["neighbors"] = sorted(set(c["neighbors"]))
        c.pop("_file_seq")
    return cells


def load_corpus_jsonl(path: str) -> list[dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return from_corpus_rows(rows)


def terrain_hash(cells: list[dict]) -> str:
    return fnv1a_64_hex(canonical_dumps(cells))


def desirability(cell: dict, attention_bias_q16: int) -> int:
    """Q16 desirability = taint*(1+bias) + entry/2, saturated at Q16_DENOM."""
    raw = (cell["taint_q16"] * (Q16_DENOM + attention_bias_q16)) // Q16_DENOM \
        + cell["entry_q16"] // 2
    return min(raw, Q16_DENOM)
