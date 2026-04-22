from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

import networkx as nx

from topomux.topologies import validate


@dataclass
class NodeMapping:
    """Maps a flat rank index to nXX:aclY hardware coordinates."""

    fpgas_per_node: int = 3

    def node_id(self, rank: int) -> int:
        return rank // self.fpgas_per_node

    def acl_id(self, rank: int) -> int:
        return rank % self.fpgas_per_node

    def format(self, rank: int) -> str:
        return f"n{self.node_id(rank):02d}:acl{self.acl_id(rank)}"


class HardwareBackend:
    """Generates --fpgalink=... strings for any toolchain that consumes the
    Xilinx / oneAPI fpgalink syntax. Callers prepend their own tool name
    (changeFPGAlinks, changeFPGAlinksXilinx, ...)."""

    def __init__(self, mapping: NodeMapping | None = None):
        self.mapping = mapping or NodeMapping()

    def emit(self, graph: nx.Graph) -> list[str]:
        """Return list of --fpgalink=... strings, one per edge."""
        validate(graph)
        links: list[str] = []
        for (r1, l1), (r2, l2) in graph.edges:
            src = f"{self.mapping.format(r1)}:ch{l1}"
            dst = f"{self.mapping.format(r2)}:ch{l2}"
            links.append(f"--fpgalink={src}-{dst}")
        return links

    def emit_gui_url(self, graph: nx.Graph) -> str:
        """Return fpgalink-gui URL for visualization."""
        links_str = " ".join(self.emit(graph))
        encoded = quote(links_str, safe="")
        return (
            f"https://pc2.github.io/fpgalink-gui/index.html?import={encoded}"
        )
