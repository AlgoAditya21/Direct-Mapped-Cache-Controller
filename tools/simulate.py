#!/usr/bin/env python3
"""Standalone behavioral simulator for the Direct-Mapped Cache Controller.

Executes the identical 3-phase memory trace (Sequential, Repeated, Random)
defined in tb/tb_cache.v without requiring Icarus Verilog installed.
"""

HIT_TIME = 1
MISS_PENALTY = 10

NUM_LINES = 64
BLOCK_SIZE = 16

valid_ram = [0] * NUM_LINES
tag_ram = [0] * NUM_LINES
data_ram = [0] * NUM_LINES

stat_accesses = 0
stat_hits = 0
stat_misses = 0

def access(addr):
    global stat_accesses, stat_hits, stat_misses
    stat_accesses += 1
    offset = addr & 0xF
    index = (addr >> 4) & 0x3F
    tag = (addr >> 10) & 0x3FFFFF

    if valid_ram[index] == 1 and tag_ram[index] == tag:
        stat_hits += 1
        return True
    else:
        stat_misses += 1
        valid_ram[index] = 1
        tag_ram[index] = tag
        return False

def report_phase(name, base_acc, base_hit, base_miss):
    acc = stat_accesses - base_acc
    hit = stat_hits - base_hit
    miss = stat_misses - base_miss
    hit_ratio = 0.0 if acc == 0 else hit / acc
    miss_ratio = 0.0 if acc == 0 else miss / acc
    amat = HIT_TIME + miss_ratio * MISS_PENALTY

    print("---------------------------------------------")
    print(f" PHASE: {name}")
    print(f"   accesses   = {acc}")
    print(f"   hits       = {hit}")
    print(f"   misses     = {miss}")
    print(f"   hit ratio  = {hit_ratio:.3f}")
    print(f"   miss ratio = {miss_ratio:.3f}")
    print(f"   AMAT       = {amat:.3f} cycles  (hit={HIT_TIME} + miss_ratio*{MISS_PENALTY})")

def main():
    global stat_accesses, stat_hits, stat_misses
    print("================================================================")
    print(" Direct-Mapped Cache Simulation (1 KB, 16B Block, 64 Lines)")
    print("================================================================")

    # Phase 1: Sequential Access (Spatial Locality)
    b_acc, b_hit, b_miss = stat_accesses, stat_hits, stat_misses
    for k in range(64):
        access(k * 4)
    report_phase("SEQUENTIAL", b_acc, b_hit, b_miss)

    # Phase 2: Repeated Access (Temporal Locality)
    b_acc, b_hit, b_miss = stat_accesses, stat_hits, stat_misses
    for k in range(40):
        access(0x00010000 + (k % 4) * 64)
    report_phase("REPEATED", b_acc, b_hit, b_miss)

    # Phase 3: Random Access (Zero / Low Locality)
    b_acc, b_hit, b_miss = stat_accesses, stat_hits, stat_misses
    rnd = 0xACE12345
    for _ in range(200):
        rnd = (rnd ^ ((rnd << 13) & 0xFFFFFFFF)) & 0xFFFFFFFF
        rnd = (rnd ^ (rnd >> 17)) & 0xFFFFFFFF
        rnd = (rnd ^ ((rnd << 5) & 0xFFFFFFFF)) & 0xFFFFFFFF
        access(rnd & 0xFFFF)
    report_phase("RANDOM", b_acc, b_hit, b_miss)

    # Overall Summary
    print("=============================================")
    print(" OVERALL")
    print(f"   total accesses = {stat_accesses}")
    print(f"   total hits     = {stat_hits}")
    print(f"   total misses   = {stat_misses}")
    print(f"   overall hit ratio  = {(stat_hits / stat_accesses):.3f}")
    print(f"   overall AMAT       = {HIT_TIME + (stat_misses / stat_accesses) * MISS_PENALTY:.3f} cycles")
    print("=============================================")

if __name__ == "__main__":
    main()
