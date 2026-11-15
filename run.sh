#!/usr/bin/env bash
# Build + simulate the direct-mapped cache with Icarus Verilog.
set -e
cd "$(dirname "$0")"

echo ">> Compiling..."
iverilog -g2012 -I rtl -o build/cache_sim \
    rtl/main_memory.v \
    rtl/cache_controller.v \
    tb/tb_cache.v

echo ">> Running simulation..."
vvp build/cache_sim

echo ">> Done. Waveform: cache.vcd (open with: gtkwave cache.vcd)"
