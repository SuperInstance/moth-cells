"""Walk a hunter across terrain for N ticks, booking every event."""
from __future__ import annotations

from .model import Hunter
from .receipts import (chain, finding_row, hunt_header, refusal_row)
from .rules import probe, rule_hunter_move


def walk(genome, cells: list[dict], ticks: int, *, probe_at: int | None = None,
         start_energy_q16: int = 1 << 16):
    """Run the kernel. Returns (hunter, sealed_rows).

    probe_at: if set, probe() fires when the hunter lands on that cell index
    (decoy/refusal semantics included). Deaths book REFUSAL rows; dormancy
    books one REFUSAL (boredom) at onset; moves are summarized in the header,
    not per-row — the walk is re-derivable from dice_seed + genome_hash.
    """
    hunter = Hunter(genome=genome, pos=0, energy_q16=start_energy_q16)
    rows: list[dict] = [hunt_header(hunter, cells, ticks)]
    booked_dormancy = False
    probed_cells: set[int] = set()
    for tick in range(ticks):
        if not hunter.alive:
            break
        prev_pos = hunter.pos
        event = rule_hunter_move(hunter, cells, tick)
        if event["type"] == "death":
            rows.append(refusal_row(event, hunter, tick))
            break
        if event.get("dormant") and not booked_dormancy:
            rows.append(refusal_row({"reason": "boredom_dormancy",
                                     "cell_id": cells[hunter.pos]["cell_id"]},
                                    hunter, tick))
            booked_dormancy = True
        # probe once per ARRIVAL at the probed cell (tick 0 counts as an
        # arrival for a hunter that starts there), not every resident tick
        arrived = hunter.pos != prev_pos or tick == 0
        if probe_at is not None and hunter.pos == probe_at and arrived \
                and probe_at not in probed_cells:
            probed_cells.add(probe_at)
            p = probe(hunter, cells)
            if p["type"] == "claim":
                rows.append(finding_row(p, hunter, tick))
            else:
                rows.append(refusal_row(p, hunter, tick))
    return hunter, chain(rows)


def replay(genome, cells: list[dict], ticks: int, *, probe_at: int | None = None,
           start_energy_q16: int = 1 << 16):
    """Determinism proof: walk() twice from the same genome over the same
    terrain must seal byte-identical rows. Numbers re-derived, never trusted.
    """
    _, rows_a = walk(genome, cells, ticks, probe_at=probe_at,
                     start_energy_q16=start_energy_q16)
    _, rows_b = walk(genome, cells, ticks, probe_at=probe_at,
                     start_energy_q16=start_energy_q16)
    from .vendor_canonical import canonical_dumps
    a = [canonical_dumps(r) for r in rows_a]
    b = [canonical_dumps(r) for r in rows_b]
    return a == b
