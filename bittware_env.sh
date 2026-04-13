#!/bin/bash
# Load Bittware FPGA modules for linktest.
# Usage: source bittware_env.sh [OCL_SDK] [OCL_BSP]

OCL_SDK="${1:-21.4.0}"
OCL_BSP="${2:-20.4.0_max}"

ml fpga
ml intel/opencl_sdk/$OCL_SDK
ml bittware/520n/$OCL_BSP
ml changeFPGAlinks
ml intel/testFPGAlinks-opencl
