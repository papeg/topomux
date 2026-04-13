from __future__ import annotations

import os
from pathlib import Path

import networkx as nx

from topomux.topologies import ranks, validate


class AuroraFlowNaming:
    """Flat directory naming: aurora_r{rank}_i{ch}_tx / _rx."""

    def tx_path(self, base_dir: Path, rank: int, channel: int) -> Path:
        return base_dir / f"aurora_r{rank}_i{channel}_tx"

    def rx_path(self, base_dir: Path, rank: int, channel: int) -> Path:
        return base_dir / f"aurora_r{rank}_i{channel}_rx"

    def directories(self, base_dir: Path, rank_ids: list[int]) -> list[Path]:
        return [base_dir]


class P2pFpgaNaming:
    """Per-rank directory naming: rank{i}/channel_{c} with numbered symlinks."""

    def tx_path(self, base_dir: Path, rank: int, channel: int) -> Path:
        return base_dir / f"rank{rank}" / f"channel_{channel}"

    def rx_path(self, base_dir: Path, rank: int, channel: int) -> Path:
        link_num = channel * 2 + 2
        return base_dir / f"rank{rank}" / str(link_num)

    def local_rx_path(
        self, base_dir: Path, rank: int, channel: int
    ) -> Path:
        link_num = channel * 2 + 1
        return base_dir / f"rank{rank}" / str(link_num)

    def directories(self, base_dir: Path, rank_ids: list[int]) -> list[Path]:
        return [base_dir / f"rank{r}" for r in rank_ids]


def _symlink_target(target: Path, link: Path) -> str:
    """Absolute base-dir → absolute target. Relative base-dir → relative target."""
    if target.is_absolute():
        return str(target)
    return os.path.relpath(target, link.parent)


class EmulationBackend:
    """Creates unix FIFOs and symlinks for software emulation."""

    def __init__(
        self,
        naming: AuroraFlowNaming | P2pFpgaNaming,
        base_dir: Path,
    ):
        self.naming = naming
        self.base_dir = Path(base_dir)

    def emit(self, graph: nx.Graph, dry_run: bool = False) -> list[str]:
        """Create FIFOs and symlinks. Returns list of actions taken."""
        validate(graph)
        actions: list[str] = []
        rank_ids = ranks(graph)

        for d in self.naming.directories(self.base_dir, rank_ids):
            actions.append(f"mkdir -p {d}")
            if not dry_run:
                d.mkdir(parents=True, exist_ok=True)

        created_fifos: set[Path] = set()

        # For P2pFpgaNaming, create local odd-numbered symlinks
        if isinstance(self.naming, P2pFpgaNaming):
            all_channels: dict[int, set[int]] = {}
            for r, ch in graph.nodes:
                all_channels.setdefault(r, set()).add(ch)
            for r, chs in sorted(all_channels.items()):
                for ch in sorted(chs):
                    fifo = self.naming.tx_path(self.base_dir, r, ch)
                    if fifo not in created_fifos:
                        actions.append(f"mkfifo {fifo}")
                        if not dry_run:
                            os.mkfifo(fifo)
                        created_fifos.add(fifo)
                    local_rx = self.naming.local_rx_path(self.base_dir, r, ch)
                    target = _symlink_target(fifo, local_rx)
                    actions.append(f"ln -s {target} {local_rx}")
                    if not dry_run:
                        local_rx.symlink_to(target)

        for (r_a, ch_a), (r_b, ch_b) in graph.edges:
            is_self_loop = (r_a, ch_a) == (r_b, ch_b)

            tx_a = self.naming.tx_path(self.base_dir, r_a, ch_a)
            if tx_a not in created_fifos:
                actions.append(f"mkfifo {tx_a}")
                if not dry_run:
                    os.mkfifo(tx_a)
                created_fifos.add(tx_a)

            if not is_self_loop:
                tx_b = self.naming.tx_path(self.base_dir, r_b, ch_b)
                if tx_b not in created_fifos:
                    actions.append(f"mkfifo {tx_b}")
                    if not dry_run:
                        os.mkfifo(tx_b)
                    created_fifos.add(tx_b)

            rx_a = self.naming.rx_path(self.base_dir, r_a, ch_a)
            if is_self_loop:
                target = _symlink_target(tx_a, rx_a)
                actions.append(f"ln -s {target} {rx_a}")
                if not dry_run:
                    rx_a.symlink_to(target)
            else:
                target_a = _symlink_target(tx_b, rx_a)
                actions.append(f"ln -s {target_a} {rx_a}")
                if not dry_run:
                    rx_a.symlink_to(target_a)

                rx_b = self.naming.rx_path(self.base_dir, r_b, ch_b)
                target_b = _symlink_target(tx_a, rx_b)
                actions.append(f"ln -s {target_b} {rx_b}")
                if not dry_run:
                    rx_b.symlink_to(target_b)

        return actions
