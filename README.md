# moth-cells

**Kernel 1: cellular predation over corpus terrain.** Hunters walk a
CorpusIndex lattice seeded by a Genome. Energy is Q16. Dice is
splitmix64(genome.seed, tick) — deterministic, replayable, never floats.
Every walk seals as a chained receipt; `verify` re-derives from residue.

## The kernel in one paragraph

A **hunter** is a `Genome` {seed, move_weights, attention_bias} placed on a
**terrain** built from `moth-corpus` canonical rows — cells are
`(file, fn)` surfaces with `taint_q16` / `entry_q16` and adjacency from
file chains plus cross-file links. Each tick, `rule_hunter_move` walks to
the most desirable neighbor (ties broken by dice, never by float). Visiting
taint-rich cells gains energy; moving costs it. **Death books a REFUSAL row**
— a death is a REFUSAL row, not a deletion. Sustained boredom in poor regions
triggers **dormancy**, booked once as a boredom refusal; dormant hunters wake
only on dice luck — dormancy is not costume. Probing a cell books a
**FINDING/v1** row; probing a **decoy** (sink-verified safe) books a
REFUSAL with `polarity=positive` — refusing bait is good hunting. Every
FINDING carries `genome_hash` + `dice_seed`, so any genome's walk is
replayable from the chain.

## Family position

```
moth-ledger    envelopes + chain law + verify          (main @ e95c786)
moth-corpus    CorpusIndex: repos → receipted surface  (PR #1)
moth-honest    the evaluator: planted truth, honest cost (PR #1)
moth-cells     kernel 1: cellular predation            (this repo)
moth-runner    campaigns, witness.jsonl, throttle seam (next)
```

Consumes terrain from `moth-corpus` canonical JSONL (no import — receipts,
not dependencies). Feeds `moth-honest` for evaluation of real hunters.

## Usage

```bash
pip install -e .
moth-cells walk --corpus corpus.jsonl --genome 0xC0CA9E:49152,16384,0:8192 \
    --ticks 60 --probe-at 5 -o walk.jsonl
moth-cells verify walk.jsonl
```

Genome spec: `seed:weights_csv:attention_bias_q16`.

## The demo walk

`examples/demo_walk.py` runs genome `aff3c14ae16cd68f` over a synthetic
6-cell terrain for 60 ticks with a probe on the decoy cell. The sealed
receipt ships in-repo (`examples/demo.walk.jsonl`) — CI regenerates it and
refuses drift. Current honest result:

```
rows: HUNT/v1 x1, REFUSAL/v1 x1 (decoy_resisted)
hunter: alive, energy 65536/65536 (saturated, never above full)
```

The hunter found the hottest-looking cell in the terrain and refused it,
because the terrain said it was bait. That refusal is the product.

## Doctrine (from Ideator B, institutionalized)

- A finding is a quilt cell or it doesn't exist.
- A death is a REFUSAL row, not a deletion.
- Numbers are re-derived, never trusted (`replay()` demands byte-identical
  sealed rows across two runs of the same genome).
- False positives are never deleted; decoy refusals are `polarity=positive`.
- Energy saturates at 1.0 — hunts that never starve and never get bored are
  hallucinating.
- Stdlib only. Q16 everywhere. Vendored canonical+hashes (family chain).

## Tests

26 green: adjacency, desirability, dice determinism, genome identity,
energy accounting + saturation, starvation deaths, dormancy, decoy refusals,
FINDING replay fields, tamper detection, replay byte-identity, CLI roundtrip.

```bash
python -m pytest
```
