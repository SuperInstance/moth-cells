"""Hunter genomes, seeded dice, and the energy model.

A genome is {seed, move_weights, attention_bias} — walk weights, not identity.
Identity is the hash of the canonical serialization. The dice is a splitmix64
PRNG keyed by (genome_seed, tick): deterministic, replayable, never floats.
"""
from __future__ import annotations

from dataclasses import dataclass

from .vendor_canonical import canonical_dumps
from .vendor_hashes import fnv1a_64, fnv1a_64_hex

Q16_DENOM = 65536


def q16(value: float) -> int:
    """Deterministic truncation toward zero; documented, substrate-identical."""
    return int(value * Q16_DENOM)


def from_q16(value: int) -> float:
    return value / Q16_DENOM


def splitmix64(state: int) -> tuple[int, int]:
    """One splitmix64 round. Returns (output, new_state)."""
    state = (state + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    z = state
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    return z ^ (z >> 31), state


@dataclass(frozen=True)
class Genome:
    seed: int
    move_weights: tuple[int, ...]  # Q16 weights per move direction, sum = Q16_DENOM
    attention_bias: int            # Q16, extra pull toward high-taint cells
    genome_id: str = ""            # filled by __post_init__ hash

    def __post_init__(self):
        object.__setattr__(self, "genome_id", self.hash_id())

    def hash_id(self) -> str:
        payload = {
            "seed": self.seed,
            "move_weights": list(self.move_weights),
            "attention_bias": self.attention_bias,
        }
        return fnv1a_64_hex(canonical_dumps(payload))

    def dice(self, tick: int) -> int:
        """Deterministic per-(genome,tick) output in [0, 2^64)."""
        out, _ = splitmix64((self.seed ^ (tick * 0x9E3779B97F4A7C15))
                            & 0xFFFFFFFFFFFFFFFF)
        return out


@dataclass
class Hunter:
    genome: Genome
    pos: int                       # cell index into terrain
    energy_q16: int
    alive: bool = True
    dormant: bool = False
    bored_ticks: int = 0
    moves: int = 0
    findings: int = 0


ENERGY_GAIN_Q16 = q16(0.25)        # visiting a high-taint cell
ENERGY_MOVE_COST_Q16 = q16(0.04)   # per move
ENERGY_DORMANCY_FLOOR_Q16 = q16(0.10)
BOREDOM_THRESHOLD_TICKS = 3
TAINT_RICH_THRESHOLD_Q16 = q16(0.5)
