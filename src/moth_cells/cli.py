"""moth-cells CLI: run a walk, verify a sealed walk."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .terrain import load_corpus_jsonl
from .vendor_canonical import canonical_dumps
from .vendor_hashes import assert_pins
from .walk import replay, walk


def _genome_from(spec: str):
    from .model import Genome
    seed_s, weights_s, bias_s = spec.split(":")
    weights = tuple(int(w) for w in weights_s.split(","))
    return Genome(seed=int(seed_s, 0), move_weights=weights,
                  attention_bias=int(bias_s))


def cmd_walk(args: argparse.Namespace) -> int:
    assert_pins()
    cells = load_corpus_jsonl(args.corpus)
    genome = _genome_from(args.genome)
    hunter, rows = walk(genome, cells, args.ticks,
                        probe_at=args.probe_at,
                        start_energy_q16=args.energy)
    assert replay(genome, cells, args.ticks, probe_at=args.probe_at,
                  start_energy_q16=args.energy)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(canonical_dumps(r).decode("utf-8") + "\n")
    print(f"walk sealed -> {args.output} (hunter {genome.genome_id}, "
          f"moves={hunter.moves}, alive={hunter.alive})")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    from .receipts import verify
    rows = [json.loads(l) for l in Path(args.walk_file).read_text(encoding="utf-8").splitlines() if l.strip()]
    ok, errors = verify(rows)
    if ok:
        print(f"OK: {args.walk_file} — walk receipt intact")
        return 0
    for e in errors:
        print(f"BROKEN: {e}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="moth-cells",
        description="Kernel 1: cellular predation over corpus terrain",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_walk = sub.add_parser("walk", help="run a seeded hunter walk over a corpus terrain")
    p_walk.add_argument("--corpus", required=True, help="canonical JSONL corpus rows")
    p_walk.add_argument("--genome", required=True,
                        help="seed:weights_csv:bias_q16  e.g. 0xC0CA9E:49152,16384,0:8192")
    p_walk.add_argument("--ticks", type=int, required=True)
    p_walk.add_argument("--probe-at", type=int, default=None)
    p_walk.add_argument("--energy", type=int, default=65536)
    p_walk.add_argument("-o", "--output", required=True)
    p_walk.set_defaults(func=cmd_walk)

    p_ver = sub.add_parser("verify", help="verify a sealed walk")
    p_ver.add_argument("walk_file")
    p_ver.set_defaults(func=cmd_verify)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
