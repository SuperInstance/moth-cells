"""The predation kernel: rule_hunter_move + energy + death/dormancy booking.

Doctrine (Ideator B): a finding is a quilt cell or it doesn't exist; a death
is a REFUSAL row, not a deletion; numbers are re-derived, never trusted.
"""
from __future__ import annotations

from .model import (BOREDOM_THRESHOLD_TICKS, ENERGY_DORMANCY_FLOOR_Q16,
                    ENERGY_GAIN_Q16, ENERGY_MOVE_COST_Q16, Q16_DENOM,
                    TAINT_RICH_THRESHOLD_Q16, Hunter, Genome, q16)
from .terrain import desirability


def _weighted_choice(candidates: list[tuple[int, int]], dice: int) -> int:
    """candidates: [(cell_index, weight_q16), ...]; dice in [0, 2^64).

    Weighted choice without floats: scale the dice into the weight space.
    """
    total = sum(w for _, w in candidates)
    if total <= 0:
        return candidates[0][0]
    point = (dice % (1 << 64)) * total >> 64
    acc = 0
    for idx, w in candidates:
        acc += w
        if point < acc:
            return idx
    return candidates[-1][0]


def rule_hunter_move(hunter: Hunter, cells: list[dict], tick: int) -> dict:
    """One tick. Returns an event dict (booking handled by receipts).

    Dormant hunters only wake on dice luck (1/16 chance per tick) — dormancy
    is not costume; waking is a surprise event, not a churn event.
    """
    if not hunter.alive:
        return {"type": "corpse"}
    cell = cells[hunter.pos]

    if hunter.dormant:
        if hunter.genome.dice(tick) % 16 == 0:
            hunter.dormant = False
            hunter.bored_ticks = 0
            return {"type": "wake", "pos": hunter.pos}
        return {"type": "dormant"}

    neighbors = [n for n in cell["neighbors"] if 0 <= n < len(cells)]
    if not neighbors:
        # No moves: starvation by isolation — a trap with one room is a lie.
        return _starve(hunter, cells, tick, "isolated")

    scored = [(n, desirability(cells[n], hunter.genome.attention_bias))
              for n in neighbors]
    best = max(s for _, s in scored)
    top = [(n, s) for n, s in scored if s == best]
    if len(top) > 1:
        chosen = _weighted_choice(top, hunter.genome.dice(tick))
    else:
        chosen = top[0][0]

    hunter.pos = chosen
    hunter.moves += 1
    hunter.energy_q16 -= ENERGY_MOVE_COST_Q16
    dest = cells[chosen]

    if dest["taint_q16"] >= TAINT_RICH_THRESHOLD_Q16:
        hunter.energy_q16 = min(hunter.energy_q16 + ENERGY_GAIN_Q16, Q16_DENOM)
        hunter.bored_ticks = 0
    else:
        hunter.bored_ticks += 1

    event = {"type": "move", "to": chosen}

    if hunter.bored_ticks >= BOREDOM_THRESHOLD_TICKS \
            and hunter.energy_q16 <= ENERGY_DORMANCY_FLOOR_Q16 + ENERGY_GAIN_Q16:
        hunter.dormant = True
        event["dormant"] = True
        return event

    if hunter.energy_q16 <= 0:
        return _starve(hunter, cells, tick, "starved")
    return event


def _starve(hunter: Hunter, cells: list[dict], tick: int, reason: str) -> dict:
    hunter.alive = False
    cell = cells[hunter.pos]
    return {"type": "death", "reason": reason, "pos": hunter.pos,
            "cell_id": cell["cell_id"], "tick": tick}


def probe(hunter: Hunter, cells: list[dict]) -> dict:
    """The hunter claims the current cell. On a decoy the claim is refused
    with polarity=positive (refusing bait is good hunting). On a clean cell
    the claim still books — false positives are never deleted."""
    cell = cells[hunter.pos]
    if cell.get("decoy") and cell.get("sink_verified_safe"):
        return {"type": "refusal", "reason": "decoy_resisted", "polarity": "positive",
                "cell_id": cell["cell_id"]}
    hunter.findings += 1
    return {"type": "claim", "cell_id": cell["cell_id"],
            "file": cell["file"], "fn": cell["fn"],
            "taint_q16": cell["taint_q16"], "pos": hunter.pos}
