"""moth-cells — kernel 1: cellular predation over corpus terrain.

Hunters walk a CorpusIndex lattice seeded by a Genome. Energy is Q16;
dice is splitmix64(genome.seed, tick) — deterministic, replayable, never
floats. Deaths book REFUSAL rows (a death is a REFUSAL row, not a deletion);
dormancy books boredom refusals; decoy refusals carry polarity=positive.
FINDING rows carry genome_hash + dice_seed so any genome's walk is
replayable from the chain.
"""

from .model import (BOREDOM_THRESHOLD_TICKS, ENERGY_DORMANCY_FLOOR_Q16,
                    ENERGY_GAIN_Q16, ENERGY_MOVE_COST_Q16, Genome, Hunter,
                    Q16_DENOM, from_q16, q16, splitmix64)
from .receipts import chain, verify
from .rules import probe, rule_hunter_move
from .terrain import desirability, from_corpus_rows, load_corpus_jsonl, terrain_hash
from .vendor_hashes import PINNED_VECTORS, assert_pins, fnv1a_64, fnv1a_64_hex
from .walk import replay, walk

__version__ = "0.1.0"

__all__ = [
    "BOREDOM_THRESHOLD_TICKS",
    "ENERGY_DORMANCY_FLOOR_Q16",
    "ENERGY_GAIN_Q16",
    "ENERGY_MOVE_COST_Q16",
    "Genome",
    "Hunter",
    "PINNED_VECTORS",
    "Q16_DENOM",
    "__version__",
    "assert_pins",
    "chain",
    "desirability",
    "fnv1a_64",
    "fnv1a_64_hex",
    "from_corpus_rows",
    "from_q16",
    "load_corpus_jsonl",
    "probe",
    "q16",
    "replay",
    "rule_hunter_move",
    "splitmix64",
    "terrain_hash",
    "verify",
    "walk",
]
