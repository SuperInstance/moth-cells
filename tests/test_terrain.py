"""Terrain + model semantics."""
from moth_cells import (Genome, assert_pins, desirability, from_corpus_rows,
                        q16, terrain_hash)
from moth_cells.model import splitmix64


def _rows():
    return [
        {"file_path": "a.rs", "language": "rust", "loc": 10,
         "surface": {"name": "parse", "entry_points": 65536 // 2, "taint_marks": 65536 * 3 // 4}},
        {"file_path": "a.rs", "language": "rust", "loc": 20,
         "surface": {"name": "render", "entry_points": 65536 // 4, "taint_marks": 65536 // 4}},
        {"file_path": "b.rs", "language": "rust", "loc": 5,
         "surface": {"name": "main", "entry_points": 65536, "taint_marks": 0}},
    ]


def test_pins():
    assert_pins()


def test_cells_from_corpus_rows():
    cells = from_corpus_rows(_rows())
    assert len(cells) == 3
    assert cells[0]["cell_id"] == "a.rs:parse"


def test_adjacency_same_file_chain():
    cells = from_corpus_rows(_rows())
    # a.rs:parse is first in its file: only in-file link to render
    assert cells[0]["neighbors"] == [1]
    assert 0 in cells[1]["neighbors"]  # render links back + cross-file


def test_adjacency_cross_file_link():
    cells = from_corpus_rows(_rows())
    assert 2 in cells[1]["neighbors"]  # last of a.rs links to first of b.rs


def test_terrain_hash_binds_content():
    a = terrain_hash(from_corpus_rows(_rows()))
    modified = _rows()
    modified[0]["surface"]["taint_marks"] = 1
    b = terrain_hash(from_corpus_rows(modified))
    assert a != b


def test_desirability_saturates():
    cell = {"taint_q16": 65536, "entry_q16": 65536}
    assert desirability(cell, 65536 // 4) <= 65536


def test_splitmix64_deterministic():
    a, sa = splitmix64(42)
    b, sb = splitmix64(42)
    assert a == b and sa == sb
    c, _ = splitmix64(43)
    assert c != a


def test_genome_hash_binds_all_fields():
    g1 = Genome(seed=1, move_weights=(32768, 32768), attention_bias=0)
    g2 = Genome(seed=1, move_weights=(32768, 32768), attention_bias=1)
    g3 = Genome(seed=2, move_weights=(32768, 32768), attention_bias=0)
    assert len({g1.genome_id, g2.genome_id, g3.genome_id}) == 3


def test_genome_dice_per_tick_varies():
    g = Genome(seed=7, move_weights=(65536,), attention_bias=0)
    draws = {g.dice(t) for t in range(8)}
    assert len(draws) > 4


def test_q16_truncates_never_rounds():
    assert q16(0.5) == 32768
    assert q16(0.1) == 6553   # 6553.6 truncated, not rounded
    assert q16(0.9) == 58982  # 58982.4 truncated
