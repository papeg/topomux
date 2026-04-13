# topomux

FPGA network topology generator built on NetworkX. Defines topologies once, emits them as hardware `--fpgalink` commands or emulation FIFOs/symlinks.

## Install

```bash
source env.sh
make venv
source .venv/bin/activate
```

## CLI

```bash
# Hardware links (Xilinx, 3 FPGAs per node)
topomux ring 3 --backend hardware --fpgas-per-node 3
# → changeFPGAlinksXilinx --fpgalink=n00:acl0:ch1-n00:acl1:ch0 ...

# From topology file
topomux -f topologies/xilinx_ring.topo -b hardware --fpgas-per-node 3

# Emulation links
topomux ring 4 -b emulation --naming auroraflow --base-dir /tmp/pipes

# Dry run (print without creating)
topomux ring 4 -b emulation --dry-run

# FPGA-Link GUI URL
topomux ring 3 -b hardware --gui-url
```

## Library

```python
import topomux

# Standard topologies
g = topomux.ring(4)                       # AuroraFlow convention (ch1→next ch0)
g = topomux.ring(4, channels=(0, 1))      # p2p_fpga convention (ch0→next ch1)
g = topomux.loopback(3, channels_per_rank=2)
g = topomux.pair(3)

# From file
g = topomux.from_file("topologies/xilinx_ring.topo")

# Arbitrary
g = topomux.from_edge_list([
    ((0, 0), (1, 1)),
    ((1, 0), (2, 1)),
    ((2, 0), (0, 1)),
])

# Hardware output
hw = topomux.HardwareBackend(topomux.NodeMapping(fpgas_per_node=3))
print(hw.emit_command(g))
print(hw.emit_gui_url(g))

# Emulation output
emu = topomux.EmulationBackend(topomux.AuroraFlowNaming(), base_dir="/tmp/pipes")
emu.emit(g, dry_run=True)
```

## Topology File Format

`.topo` files support edge lists and shorthand commands. Comments with `#`.

```
# Shorthand
ring 4

# Explicit edges: rank.channel - rank.channel
0.0 - 1.1
2.0 - 0.1

# Shorthand with channel override
ring 4 0 1
loopback 3 4
pair 3 0 1
```
