#!/bin/bash
# Load Xilinx FPGA modules for linktest.
# Usage: source xilinx_env.sh [XRT_VER]

XRT_VER="${1:-2.16}"

ml fpga
ml xilinx/xrt/$XRT_VER
ml xilinx/linktest
