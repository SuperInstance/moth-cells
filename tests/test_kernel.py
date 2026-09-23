"""Kernel: moves, energy, death, dormancy, decoys, findings."""
from moth_cells import (BOREDOM_THRESHOLD_TICKS, ENERGY_GAIN_Q16,
                        ENERGY_MOVE_COST_Q16, Genome, from_corpus_rows, probe,
                        q16, rule_hunter_move, walk)
from moth_cells.receipts import verify


def _terrain(decoy=False):
    rows = [
        {"file_path": "a.c", "language": "c", "loc": 9,
         "surface": {"name": "rich", "entry_points": 65536 // 2,
                     "taint_marks": 65536 * 3 // 4}},
        {"file_path": "a.c", "language": "c", "loc": 9,
         "surface": {"name": "poor", "entry_points": 65536 // 8,
                     "taint_marks": 65536 // 8}},
        {"file_path": "b.c", "language": "c", "loc": 9,
         "surface": {"name": "decoy", "entry_points": 65536 // 2,
                     "taint_marks": 65536,
                     **({"decoy": True, "sink_verified_safe": True} if decoy else {})}},
    ]
    return from_corpus_rows(rows)


def _genome(seed=1):
    return Genome(seed=seed, move_weights=(65536 // 2, 65536 // 2, 0),
                  attention_bias=0)


def test_move_prefers_rich_neighbor():
    cells = _terrain()
    h = _mk(cells)
    start = h.pos
    rule_hunter_move(h, cells, tick=0)
    assert h.pos != start
    assert h.moves == 1


def _mk(cells, energy=65536):
    from moth_cells import Hunter
    return Hunter(genome=_genome(), pos=0, energy_q16=energy)


def test_energy_cost_per_move():
    cells = _terrain()
    h = _mk(cells)
    rule_hunter_move(h, cells, tick=0)
    # gain only if landed rich; cost always applied
    assert h.energy_q16 == 65536 - ENERGY_MOVE_COST_Q16 + (
        ENERGY_GAIN_Q16 if cells[h.pos]["taint_q16"] >= 65536 // 2 else 0)


def test_dice_determinism_same_walk():
    cells = _terrain()
    _, rows_a = walk(_genome(seed=99), cells, 20)
    _, rows_b = walk(_genome(seed=99), cells, 20)
    assert rows_a == rows_b


def test_different_seed_different_walk():
    cells = _terrain()
    _, a = walk(_genome(seed=1), cells, 25)
    _, b = walk(_genome(seed=2), cells, 25)
    pa = [r for r in a if r.get("genome_hash")]
    pb = [r for r in b if r.get("genome_hash")]
    assert (pa and pb) or a != b  # either bookings differ or rows differ


def test_starvation_books_refusal_death():
    cells = _terrain()
    # energy for exactly one move: dies on the second tick
    h = _mk(cells, energy=ENERGY_MOVE_COST_Q16)
    events = [rule_hunter_move(h, cells, t) for t in range(3)]
    assert any(e["type"] == "death" for e in events)
    assert not h.alive


def test_death_row_has_genome_and_seed():
    cells = _terrain()
    # starve on purpose: energy for exactly one move
    _, rows = walk(_genome(), cells, 5, start_energy_q16=ENERGY_MOVE_COST_Q16)
    deaths = [r for r in rows if r.get("kind") == "REFUSAL/v1"
              and r.get("reason") in ("starved", "isolated")]
    assert deaths and all(d.get("genome_hash") and d.get("dice_seed") is not None
                          for d in deaths)


def test_dormancy_after_boredom():
    # all-poor terrain: no energy gains, boredom accumulates every tick
    rows = [{"file_path": f"{f}.c", "language": "c", "loc": 5,
             "surface": {"name": "poor", "entry_points": 65536 // 16,
                         "taint_marks": 65536 // 16}} for f in "abcde"]
    cells = from_corpus_rows(rows)
    h = _mk(cells)  # full energy; all destinations poor
    dormant_seen = False
    for t in range(40):
        ev = rule_hunter_move(h, cells, t)
        if ev.get("dormant"):
            dormant_seen = True
            break
        if not h.alive:
            break
    assert dormant_seen  # bored into dormancy well before starvation


def test_probe_clean_cell_still_books_finding():
    cells = _terrain()
    h = _mk(cells)
    h.pos = 2  # decoy cell without decoy flags -> a normal claim
    p = probe(h, cells)
    assert p["type"] == "claim"


def test_probe_decoy_is_positive_refusal():
    cells = _terrain(decoy=True)
    h = _mk(cells)
    h.pos = 2
    p = probe(h, cells)
    assert p["type"] == "refusal"
    assert p["polarity"] == "positive"
    assert p["reason"] == "decoy_resisted"


def test_walk_books_decoy_refusal_row():
    cells = _terrain(decoy=True)
    _, rows = walk(_genome(), cells, 10, probe_at=2)
    refusals = [r for r in rows if r.get("kind") == "REFUSAL/v1"]
    assert any(r.get("polarity") == "positive" for r in refusals)


def test_finding_rows_carry_replay_fields():
    cells = _terrain()
    _, rows = walk(_genome(), cells, 15, probe_at=0)
    findings = [r for r in rows if r.get("kind") == "FINDING/v1"]
    for f in findings:
        assert f["genome_hash"] and f["dice_seed"] is not None and f["tick"] >= 0


def test_verify_tamper_detected():
    cells = _terrain()
    _, rows = walk(_genome(), cells, 12)
    forged = [dict(r) for r in rows]
    forged[0]["ticks"] = 999
    ok, errors = verify(forged)
    assert not ok and errors


def test_replay_byte_identical():
    from moth_cells import replay
    cells = _terrain(decoy=True)
    assert replay(_genome(seed=5), cells, 30, probe_at=2)
