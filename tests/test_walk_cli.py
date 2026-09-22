"""Energy cap + probe-once semantics + CLI."""
import json

from moth_cells import Genome, from_corpus_rows, walk
from moth_cells.cli import main
from moth_cells.rules import rule_hunter_move


def _terrain(decoy=False):
    return from_corpus_rows([
        {"file_path": "a.c", "language": "c", "loc": 9,
         "surface": {"name": "rich", "entry_points": 65536 // 2,
                     "taint_marks": 65536 * 3 // 4}},
        {"file_path": "a.c", "language": "c", "loc": 9,
         "surface": {"name": "poor", "entry_points": 65536 // 8,
                     "taint_q16": 0, "taint_marks": 65536 // 8,
                     **({"decoy": True, "sink_verified_safe": True} if decoy else {})}},
    ])


def _g():
    return Genome(seed=3, move_weights=(65536 // 2, 65536 // 2), attention_bias=0)


def test_energy_saturates_at_full():
    cells = _terrain()
    from moth_cells import Hunter
    h = Hunter(genome=_g(), pos=0, energy_q16=65536)
    for t in range(10):
        rule_hunter_move(h, cells, t)
        assert h.energy_q16 <= 65536


def test_probe_books_once_per_arrival():
    cells = _terrain()
    _, rows = walk(_g(), cells, 40, probe_at=0)  # starts at cell 0
    findings = [r for r in rows if r["kind"] == "FINDING/v1"]
    assert len(findings) == 1
    assert findings[0]["fn"] == "rich"


def test_cli_walk_verify_roundtrip(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    from moth_cells.vendor_canonical import canonical_dumps
    rows = [{"file_path": "a.c", "language": "c", "loc": 9,
             "surface": {"name": "rich", "entry_points": 32768,
                         "taint_marks": 49152}}]
    corpus.write_text("".join(
        canonical_dumps(r).decode("utf-8") + "\n" for r in rows))
    out = str(tmp_path / "walk.jsonl")
    assert main(["walk", "--corpus", str(corpus),
                 "--genome", "0xC0CA9E:65536:0",
                 "--ticks", "5", "-o", out]) == 0
    assert main(["verify", out]) == 0
