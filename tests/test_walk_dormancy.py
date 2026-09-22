"""Regression: walk()-level dormancy booking (doctrine test in moth-runner
found that refusal_row's eager default expression crashed on any event
without a 'type' key)."""
from moth_cells import Genome, from_corpus_rows, walk


def test_walk_books_dormancy_refusal_on_poor_plateau():
    cells = from_corpus_rows([
        {"file_path": f"{f}.c", "language": "c", "loc": 5,
         "surface": {"name": "poor", "entry_points": 65536 // 16,
                     "taint_marks": 65536 // 16}} for f in "abc"
    ])
    g = Genome(seed=7, move_weights=(65536 // 3,) * 3, attention_bias=0)
    hunter, rows = walk(g, cells, 40, start_energy_q16=12000)
    dormancies = [r for r in rows if r.get("reason") == "boredom_dormancy"]
    assert len(dormancies) == 1
    assert dormancies[0]["genome_hash"] == g.genome_id
    assert hunter.dormant
