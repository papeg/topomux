from __future__ import annotations

from pathlib import Path

import networkx as nx


def ring(n: int, channels: tuple[int, int] = (1, 0)) -> nx.Graph:
    """Ring topology: rank r's channels[0] connects to rank (r+1)%n's channels[1].

    Default (1, 0) matches AuroraFlow convention (ch1 → next's ch0).
    Use (0, 1) for p2p_fpga convention (ch0 → next's ch1).
    """
    g = nx.Graph()
    for r in range(n):
        next_r = (r + 1) % n
        g.add_edge((r, channels[0]), (next_r, channels[1]))
    return g


def loopback(n: int, channels_per_rank: int = 2) -> nx.Graph:
    """Loopback topology: every channel loops back to itself."""
    g = nx.Graph()
    for r in range(n):
        for ch in range(channels_per_rank):
            g.add_edge((r, ch), (r, ch))
    return g


def pair(n: int, channels: tuple[int, int] = (0, 1)) -> nx.Graph:
    """Pair topology: cross-connect two channels within each rank."""
    g = nx.Graph()
    for r in range(n):
        g.add_edge((r, channels[0]), (r, channels[1]))
    return g


def from_edge_list(edges: list[tuple]) -> nx.Graph:
    """Build topology from explicit ((rank, channel), (rank, channel)) edge tuples."""
    g = nx.Graph()
    for src, dst in edges:
        g.add_edge(tuple(src), tuple(dst))
    validate(g)
    return g


def from_file(path: str | Path) -> nx.Graph:
    """Parse a .topo file.

    Supports edge lines (``0.1 - 1.0``) and shorthand commands
    (``ring 4``, ``loopback 3 4``, ``pair 3 0 1``).
    """
    g = nx.Graph()
    path = Path(path)
    for raw_line in path.read_text().splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue

        if "-" in line and "." in line:
            _parse_edge_line(g, line)
        else:
            _parse_command_line(g, line)

    validate(g)
    return g


def _parse_edge_line(g: nx.Graph, line: str) -> None:
    left, right = line.split("-", 1)
    src = _parse_endpoint(left.strip())
    dst = _parse_endpoint(right.strip())
    g.add_edge(src, dst)


def _parse_endpoint(s: str) -> tuple[int, int]:
    parts = s.split(".")
    if len(parts) != 2:
        raise ValueError(f"Invalid endpoint '{s}', expected rank.channel")
    return int(parts[0]), int(parts[1])


_COMMANDS = {}


def _register(name: str):
    def decorator(fn):
        _COMMANDS[name] = fn
        return fn
    return decorator


@_register("ring")
def _cmd_ring(args: list[str]) -> nx.Graph:
    n = int(args[0])
    chs = (int(args[1]), int(args[2])) if len(args) >= 3 else (1, 0)
    return ring(n, channels=chs)


@_register("loopback")
def _cmd_loopback(args: list[str]) -> nx.Graph:
    n = int(args[0])
    cpr = int(args[1]) if len(args) >= 2 else 2
    return loopback(n, channels_per_rank=cpr)


@_register("pair")
def _cmd_pair(args: list[str]) -> nx.Graph:
    n = int(args[0])
    chs = (int(args[1]), int(args[2])) if len(args) >= 3 else (0, 1)
    return pair(n, channels=chs)


def _parse_command_line(g: nx.Graph, line: str) -> None:
    parts = line.split()
    cmd_name = parts[0].lower()
    if cmd_name not in _COMMANDS:
        raise ValueError(f"Unknown command '{cmd_name}' in topology file")
    sub_graph = _COMMANDS[cmd_name](parts[1:])
    g.update(sub_graph)


def ranks(g: nx.Graph) -> list[int]:
    """Return sorted list of unique rank IDs in the graph."""
    return sorted({r for r, _ch in g.nodes})


def channels(g: nx.Graph, rank: int) -> list[int]:
    """Return sorted list of channel IDs used by the given rank."""
    return sorted({ch for r, ch in g.nodes if r == rank})


def validate(g: nx.Graph) -> None:
    """Raise ValueError if any node is not a (int, int) tuple."""
    for node in g.nodes:
        if (
            not isinstance(node, tuple)
            or len(node) != 2
            or not isinstance(node[0], int)
            or not isinstance(node[1], int)
        ):
            raise ValueError(
                f"Node {node!r} is not a (rank: int, channel: int) tuple"
            )
