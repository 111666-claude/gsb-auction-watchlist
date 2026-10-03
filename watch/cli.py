"""命令行入口：跑关注列表样例。"""

import argparse

from .core import Watchers


def build_parser():
    parser = argparse.ArgumentParser(prog="auction-watchlist", description="拍卖关注")
    parser.add_argument("--sample", default="cap",
                        help="cap / dedup / merge / ttl / scan")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.sample == "cap":
        world = Watchers(per_player_max=2, ttl_ms=100000, merge_ms=0)
        for index in range(3):
            world.watch("p1", "l-%d" % index, index)
        print("pending=%d" % len(world.pending("p1", 10)))
    elif args.sample == "dedup":
        world = Watchers(per_player_max=5, ttl_ms=100000, merge_ms=0)
        world.watch("p1", "l1", 0)
        world.watch("p1", "l1", 10)
        print("pending=%d" % len(world.pending("p1", 10)))
    elif args.sample == "merge":
        world = Watchers(per_player_max=5, ttl_ms=100000, merge_ms=500)
        world.watch("p1", "l1", 0)
        world.change("l1", 0)
        print("second=%d" % len(world.change("l1", 100)))
    elif args.sample == "ttl":
        world = Watchers(per_player_max=5, ttl_ms=1000, merge_ms=0)
        world.watch("p1", "l1", 0)
        print("pending=%d" % len(world.pending("p1", 1001)))
    elif args.sample == "scan":
        world = Watchers(per_player_max=10000, ttl_ms=100000, merge_ms=0)
        for index in range(3000):
            world.watch("p-%d" % index, "l-%d" % index, 0)
        for index in range(3000):
            world.pending("p-2999", 0)
        print("scanned=%d" % world.scanned_count())
    else:
        raise SystemExit("需要 --sample cap|dedup|merge|ttl|scan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
