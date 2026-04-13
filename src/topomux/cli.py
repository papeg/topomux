from __future__ import annotations

import argparse
import sys
from pathlib import Path

from topomux import topologies
from topomux.backends.emulation import (
    AuroraFlowNaming,
    EmulationBackend,
    P2pFpgaNaming,
)
from topomux.backends.hardware import HardwareBackend, NodeMapping

TOPOLOGIES = {
    "ring": topologies.ring,
    "loopback": topologies.loopback,
    "pair": topologies.pair,
}

NAMING_CONVENTIONS = {
    "auroraflow": AuroraFlowNaming,
    "p2p_fpga": P2pFpgaNaming,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="topomux",
        description="Generate FPGA communication topologies",
    )

    # Topology source: either a named topology or a file
    topo_group = parser.add_mutually_exclusive_group(required=True)
    topo_group.add_argument(
        "topology",
        nargs="?",
        choices=list(TOPOLOGIES.keys()),
        help="Standard topology type",
    )
    topo_group.add_argument(
        "--file", "-f",
        type=Path,
        dest="topo_file",
        help="Topology file (.topo)",
    )

    parser.add_argument(
        "num_ranks",
        nargs="?",
        type=int,
        help="Number of ranks (required for standard topologies)",
    )

    parser.add_argument(
        "--channels",
        type=str,
        default=None,
        help="Channel pair override, e.g. '0,1'",
    )
    parser.add_argument(
        "--channels-per-rank",
        type=int,
        default=2,
        help="Channels per rank for loopback (default: 2)",
    )

    parser.add_argument(
        "--backend", "-b",
        choices=["emulation", "hardware"],
        required=True,
        help="Output backend",
    )

    # Emulation options
    parser.add_argument(
        "--naming",
        choices=list(NAMING_CONVENTIONS.keys()),
        default="auroraflow",
        help="Naming convention for emulation (default: auroraflow)",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("."),
        help="Base directory for emulation links",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without creating files",
    )

    # Hardware options
    parser.add_argument(
        "--fpgas-per-node",
        type=int,
        default=3,
        help="FPGAs per physical node (default: 3)",
    )
    parser.add_argument(
        "--gui-url",
        action="store_true",
        help="Print fpgalink-gui URL",
    )
    parser.add_argument(
        "--command",
        type=str,
        default="changeFPGAlinksXilinx",
        help="Hardware link tool command (default: changeFPGAlinksXilinx)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Build topology
    if args.topo_file:
        graph = topologies.from_file(args.topo_file)
    else:
        if args.num_ranks is None:
            parser.error("num_ranks is required for standard topologies")

        topo_fn = TOPOLOGIES[args.topology]

        if args.topology == "loopback":
            graph = topo_fn(
                args.num_ranks,
                channels_per_rank=args.channels_per_rank,
            )
        elif args.channels:
            ch_a, ch_b = (int(x) for x in args.channels.split(","))
            graph = topo_fn(args.num_ranks, channels=(ch_a, ch_b))
        else:
            graph = topo_fn(args.num_ranks)

    # Emit output
    if args.backend == "hardware":
        mapping = NodeMapping(fpgas_per_node=args.fpgas_per_node)
        backend = HardwareBackend(mapping=mapping)
        if args.gui_url:
            print(backend.emit_gui_url(graph))
        else:
            print(backend.emit_command(graph, cmd=args.command))

    elif args.backend == "emulation":
        naming = NAMING_CONVENTIONS[args.naming]()
        backend = EmulationBackend(naming=naming, base_dir=args.base_dir)
        actions = backend.emit(graph, dry_run=args.dry_run)
        for action in actions:
            print(action)

    return 0
