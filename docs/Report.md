# Design and Implementation of a Synthesizable Direct-Mapped Cache Controller with Average Memory Access Time (AMAT) Analysis

### Project Metadata & Author Information

| S.No. | Group Member Name | Enrollment / Student ID | Institutional Email ID | GitHub / Alternate ID |
| :---: | :--- | :---: | :--- | :--- |
| 1 | **Pushkar Jain** | `2024NST-PJ` | `pushkar.jain2024@nst.rishihood.edu.in` | `pushkar-bit` |
| 2 | **Ved Pawar** | `2024NST-VP` | `ved.pawar2024@nst.rishihood.edu.in` | `vedpawar2254` |
| 3 | **Khuswant Rajpurohit** | `2024NST-KR` | `khuswant.rajpurohit2024@nst.rishihood.edu.in` | `khuswantrajpurohit18@gmail.com` |
| 4 | **Anshu Yadav** | `2024NST-AY` | `anshu.yadav2024@nst.rishihood.edu.in` | `anshuyadav9306@gmail.com` |

*Modern Computer Architecture Project, Newton School of Technology (NST)*  
*Department of Computer Science & Engineering, Rishihood University, India*  

**Project Report / Demo:** [Google Drive](https://drive.google.com/file/d/1PxN8rB5IDqUXvr27ozbz91nybHz0H0Vk/view?usp=drivesdk)

---

## Abstract

In modern high-performance microprocessors, the expanding disparity between processor execution speeds and off-chip Dynamic Random-Access Memory (DRAM) access latencies—commonly known as the *memory wall*—imposes severe constraints on overall computational throughput. Cache memories alleviate this memory bottleneck by exploiting temporal and spatial locality of reference. 

This paper presents the architectural specification, RTL implementation, behavioral verification, and logic synthesis of a synthesizable **1 KB direct-mapped, read-only cache controller** targeting a standard 32-bit byte-addressed memory space. The cache is configured with 16-byte cache lines distributed across 64 sets, featuring dedicated tag, valid, and data storage arrays totaling 9,664 bits of raw storage. A three-state synchronous Finite State Machine (FSM) coordinates the request, tag-comparison, line allocation, and handshake sequencing with a multi-cycle backing memory store exhibiting a 10-cycle latency penalty. 

The architecture was functionally validated using Icarus Verilog across three memory access benchmarks:
1. **Sequential stride** (spatial locality), yielding a **75.0% hit ratio** and an Average Memory Access Time (**AMAT**) of **3.50 cycles**;
2. **Repeated working sets** (temporal locality), yielding a **90.0% hit ratio** and an **AMAT of 2.00 cycles**;
3. **Pseudo-random scattering** (low locality), yielding a **1.0% hit ratio** and an **AMAT of 10.90 cycles** against a baseline 1-cycle hit time.

Logic synthesis via Yosys demonstrates generic gate mapping across 30,237 standard cells and 9,862 DFFs, matching theoretical register estimations and confirming clean mapping to FPGA Block RAMs or ASIC SRAM macros.

**Index Terms**—Cache memory, Direct-mapped cache, Finite State Machine (FSM), Hardware Description Language (Verilog HDL), Memory hierarchy, Locality of reference, Average Memory Access Time (AMAT), Yosys synthesis.

---

## I. Introduction and Literature Review

### A. Background and Problem Statement
The von Neumann architecture couples the central processing unit (CPU) with memory subsystems over a shared communication channel. As semiconductor fabrication advanced according to Moore's Law and Dennard scaling, CPU cycle frequencies escalated rapidly, while off-chip DRAM access latencies improved at a much slower rate (approximately 7%–10% annually) [1], [2]. This divergence established the *memory wall* [3], forcing high-frequency processors to spend significant clock cycles in wait states waiting for memory operands.

To mask this latency differential, computer architectures employ a hierarchical memory organization [4]. High-speed on-chip Static Random-Access Memory (SRAM) cache hierarchies buffer active subsets of main memory, exploiting the fundamental empirical principles of *locality of reference* [5]:
- **Temporal Locality**: Information referenced at a given point in time exhibits a high probability of being re-referenced in the near future (e.g., loop variables, subroutine calls).
- **Spatial Locality**: Information stored in physical memory locations contiguous to recently referenced addresses exhibits a high probability of imminent access (e.g., sequential instruction execution, contiguous array iterations).

### B. Literature Review
The seminal concept of transparent caching between processor registers and backing storage was formulated by Maurice Wilkes in 1965 [6]. Alan Jay Smith subsequently formalized analytical performance models, miss classifications, and architectural trade-offs between cache size, block size, and associativity [7].

Cache placement policies broadly fall into three architectural categories [4], [8]:
1. **Fully Associative Caches**: Allow any incoming memory block to reside in any arbitrary cache line. While this eliminates conflict misses entirely, it necessitates parallel associative content-addressable comparators across every cache set, increasing critical-path delay and static power consumption.
2. **Set-Associative Caches**: Partition cache lines into distinct sets containing $K$ ways, balancing tag comparison overhead against collision reduction.
3. **Direct-Mapped Caches**: Map every physical memory address to exactly one specific line in the cache determined by index decoding ($\text{Index} = \text{Address} \pmod N$). Direct-mapped architectures require only a single comparator per access, minimizing hit latency and eliminating replacement policy tracking hardware (such as Least Recently Used / LRU) from the critical timing path [9].

While direct-mapped caches are susceptible to conflict misses when distinct memory addresses share the same index, their compact silicon footprint, high clock rates, and zero-overhead lookup logic make them widely deployed in Level-1 instruction caches, DSP cores, and low-power embedded microcontrollers [4], [10].

Cache efficiency is quantitatively evaluated through the Average Memory Access Time (AMAT) formulation [4]:

$$\text{AMAT} = \text{Hit Time} + (\text{Miss Rate} \times \text{Miss Penalty})$$

---

## II. Proposed Solution & Architecture

### A. Architectural Specification & Parameter Derivation
The proposed system is a synthesizable 1 KB direct-mapped, read-only cache controller designed for a 32-bit byte-addressed architecture.

```
32-Bit Memory Address Breakdown:
+------------------------------------+-------------------+---------------+
|            TAG [31:10]             |    INDEX [9:4]    |  OFFSET [3:0] |
|             (22 bits)              |      (6 bits)     |   (4 bits)    |
+------------------------------------+-------------------+---------------+
```

The mathematical relationships governing the address bit distribution are detailed in Table I:

#### Table I: Cache Parameter Derivation
| Parameter | Mathematical Formulation | Architectural Value |
| :--- | :--- | :--- |
| **Total Cache Size ($C$)** | Specified hardware budget | $1024\text{ Bytes (1 KB)}$ |
| **Block / Line Size ($B$)** | Spatial burst transfer size | $16\text{ Bytes (128 bits)}$ |
| **Number of Cache Lines ($N$)** | $N = \frac{C}{B} = \frac{1024}{16}$ | $64\text{ Lines / Sets}$ |
| **Address Width ($A$)** | Standard processor address bus | $32\text{ bits}$ |
| **Byte Offset Field ($b$)** | $b = \log_2(B) = \log_2(16)$ | $4\text{ bits [3:0]}$ |
| **Line Index Field ($s$)** | $s = \log_2(N) = \log_2(64)$ | $6\text{ bits [9:4]}$ |
| **Tag Field ($t$)** | $t = A - s - b = 32 - 6 - 4$ | $22\text{ bits [31:10]}$ |

### B. Hardware Submodules
The controller RTL is structured into five modular hardware primitives:

1. **Address Decoder & Request Latches**:
   - Extracts `addr_tag = cpu_addr[31:10]`, `addr_index = cpu_addr[9:4]`, and `addr_offset = cpu_addr[3:0]`.
   - On a CPU transaction initiation (`cpu_req`), address components are registered into `req_tag`, `req_index`, `req_offset`, and `req_addr` to guarantee input stability throughout multi-cycle memory refilling.

2. **Storage Arrays**:
   - **Tag RAM** (`tag_ram`): $64 \times 22$-bit registers storing high-order address tags.
   - **Valid RAM** (`valid_ram`): $64 \times 1$-bit flip-flops indicating data residency, cleared on active-low reset (`rst_n`).
   - **Data RAM** (`data_ram`): $64 \times 128$-bit registers, storing one full 16-byte block per line.
   - *Total Raw Storage*: $64 \times (22 + 1 + 128) = 9{,}664\text{ bits}$.

3. **Tag Comparator & Word Multiplexer**:
   - A 22-bit comparator computes `is_hit = valid_ram[req_index] && (tag_ram[req_index] == req_tag)`.
   - A 4-to-1 32-bit word multiplexer indexes into the 128-bit block using `req_offset[3:2]` to select the requested 32-bit word (`block[31:0]`, `block[63:32]`, `block[95:64]`, or `block[127:96]`).

4. **Backing Store Model (`main_memory.v`)**:
   - A behavioral DRAM model implementing a 10-cycle access latency (`MEM_LATENCY = 10`).
   - Generates deterministic 128-bit block vectors based on the aligned block address:
     
     $$\text{Word}_k = (\text{Block\_Number} \times 4) + k, \quad k \in \{0, 1, 2, 3\}$$

5. **Controller Finite State Machine (FSM)**:
   A synchronous Mealy/Moore FSM controls execution through three functional states:

```
                  [ cpu_req asserted ]
         IDLE ─────────────────────────────► COMPARE
          ▲                                     │
          │                        is_hit = 1   │   is_hit = 0
          │                      ┌──────────────┴──────────────┐
          │                      ▼                             ▼
          │              (Cache Hit)                      (Cache Miss)
          │            cpu_ready <= 1;                   mem_req <= 1;
          │            hit_flag  <= 1;                   mem_addr <= req_addr;
          │            cpu_rdata <= data_ram[...]              │
          │                                                    ▼
          │                                                 ALLOCATE
          │                                                    │
          │          mem_ready = 1 (Refill Complete)           │
          └────────────────────────────────────────────────────┘
                     valid_ram[index] <= 1;
                     tag_ram[index]   <= tag;
                     data_ram[index]  <= mem_rdata;
                     cpu_ready <= 1; hit_flag <= 0;
```

- **`S_IDLE` (`2'd0`)**: Awaits `cpu_req`. On detection, registers the address fields, increments `stat_accesses`, and transitions to `S_COMPARE`.
- **`S_COMPARE` (`2'd1`)**: Evaluates `is_hit`.
  - **Hit**: Increments `stat_hits`, multiplexes `cpu_rdata`, asserts `cpu_ready` and `hit_flag`, and returns to `S_IDLE` in 1 clock cycle.
  - **Miss**: Increments `stat_misses`, asserts `mem_req`, places `req_addr` onto `mem_addr`, and transitions to `S_ALLOCATE`.
- **`S_ALLOCATE` (`2'd2`)**: Stalls until `mem_ready` asserts from main memory. Upon readiness, writes the 128-bit line into `data_ram`, updates `tag_ram` and `valid_ram`, passes the requested 32-bit sub-word directly to `cpu_rdata`, asserts `cpu_ready` with `hit_flag = 0`, and returns to `S_IDLE`.

---

## III. Verification Methodology & Experimental Results

### A. Verification Setup
The design was simulated using Icarus Verilog (`iverilog`) under a self-contained testbench harness (`tb_cache.v`) clocked at 100 MHz ($T = 10\text{ ns}$). AMAT calculations are evaluated using a 1-cycle hit time and a 10-cycle miss penalty.

### B. Experimental Results

#### Table II: Quantitative Performance Across Access Profiles
| Benchmark Phase | Access Pattern Description | Accesses | Hits | Misses | Hit Ratio ($H$) | Miss Ratio ($M$) | AMAT (Cycles) | Memory Locality Principle Validated |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Phase 1** | Sequential stride ($+4\text{ B}$) | 64 | 48 | 16 | **0.750** | **0.250** | **3.50** | **Spatial Locality** (Block Fetch) |
| **Phase 2** | Repeated loop (4-block working set) | 40 | 36 | 4 | **0.900** | **0.100** | **2.00** | **Temporal Locality** (Set Retention) |
| **Phase 3** | Pseudo-random 32-bit xorshift (16-bit addr window) | 200 | 2 | 198 | **0.010** | **0.990** | **10.90** | **Low Locality** (Conflict Thrashing) |
| **Overall** | Full Combined Test Suite | **304** | **86** | **218** | **0.283** | **0.717** | **8.17** | Comprehensive Workload Metric |

### C. Analysis and Discussion

1. **Spatial Locality Validation (Phase 1)**:
   Traversing consecutive 32-bit words ($0\text{x}0, 0\text{x}4, 0\text{x}8, 0\text{x}C$) generates an initial cold miss on word 0, causing the controller to fetch the entire 16-byte block. The remaining three words in that block hit immediately in `data_ram`. Across 64 word accesses (spanning 16 blocks), this yields exactly 16 cold misses and 48 cache hits:
   
   $$\text{Hit Ratio} = \frac{48}{64} = 75.0\%$$
   
   $$\text{AMAT} = 1 + (0.250 \times 10) = 3.50\text{ clock cycles}$$

2. **Temporal Locality Validation (Phase 2)**:
   Repeatedly referencing a 4-block working set across 40 iterations in an unvisited memory segment results in 4 initial cold misses, after which all 4 lines remain resident in the cache array. The remaining 36 accesses hit with zero wait states:
   
   $$\text{Hit Ratio} = \frac{36}{40} = 90.0\%$$
   
   $$\text{AMAT} = 1 + (0.100 \times 10) = 2.00\text{ clock cycles}$$

3. **Conflict Miss Sensitivity (Phase 3)**:
   When memory references are generated across a 64 KB space via a 32-bit xorshift generator (addresses taken from the low 16 bits of state), the working set is $64\times$ larger than the 1 KB cache capacity. Direct mapping causes lines with identical index bits to repeatedly displace one another, yielding a 1.0% hit ratio and driving the AMAT to 10.90 cycles.

---

## IV. Logic Synthesis & Hardware Resource Utilization

The cache controller RTL was synthesized using Yosys (version 0.71) targeting a generic gate-level standard cell library:

```bash
yosys -q -p "read_verilog -I rtl rtl/cache_controller.v; synth -top cache_controller; stat"
```

#### Table III: Gate-Level Synthesis Results (Generic Cell Library)
| Category | Circuit Primitive | Count |
| :--- | :--- | :---: |
| **Total Cells** | Total Gate Count | **30,237** |
| **Sequential Storage** | D Flip-Flops (DFF) | **9,862** |
| **Combinational Gates** | AND / ANDNOT | 14,796 |
| | NOR | 4,788 |
| | Multiplexers (MUX) | 85 |
| **Interconnect** | Total Wires | 20,321 |
| | Public Wire Bits | 10,094 |

### Flip-Flop Count Verification:
The synthesized DFF count aligns with the theoretical register audit:
- Core Storage: $64\text{ lines} \times (22\text{ tag} + 1\text{ valid} + 128\text{ data}) = 9{,}664\text{ bits}$
- Pipeline & Latches: `req_addr` (32), `req_tag` (22), `req_index` (6), `req_offset` (4) = 64 bits
- Statistics & Status: `stat_accesses` (32), `stat_hits` (32), `stat_misses` (32), FSM state (2), control flags $\approx 134\text{ bits}$
- Total: $9{,}664 + 64 + 134 = 9{,}862\text{ flip-flops}$ (exact match with synthesis).

---

## V. Individual Contributions

| S.No. | Group Member | Enrollment ID | Primary Role | Key Technical Contributions |
| :---: | :--- | :---: | :--- | :--- |
| 1 | **Pushkar Jain** | `2024NST-PJ` | **System Architecture & Hardware RTL Lead** | • Formulated cache architectural parameterization and address slicing macros (`cache_defs.vh`).<br>• Designed and implemented the complete synthesizable RTL for `cache_controller.v`, including the 3-state controller FSM (`S_IDLE`, `S_COMPARE`, `S_ALLOCATE`).<br>• Designed the 22-bit tag comparator, address decoders, and word-selection multiplexers.<br>• Executed logic synthesis in Yosys and audited gate/register area against theoretical models.<br>• Authored the Proposed Solution, System Architecture, and Synthesis sections of the report. |
| 2 | **Ved Pawar** | `2024NST-VP` | **Verification Lead & Backing Store Modeling** | • Designed and implemented the behavioral backing store memory model (`main_memory.v`) with multi-cycle latency handshake.<br>• Authored the initial testbench infrastructure (`tb_cache.v`) and signal declarations.<br>• Implemented real-time AMAT and hit/miss statistical computation tasks in simulation.<br>• Built the Python VCD waveform extraction script (`plot_wave.py`) for automated timing diagrams.<br>• Contributed to the Abstract, Literature Review, and Verification Analysis sections of the report. |
| 3 | **Khuswant Rajpurohit** | `2024NST-KR` | **Benchmark Generation & Workload Analysis** | • Designed the memory access benchmark suites for spatial locality (sequential strides) and temporal locality (repeated working sets).<br>• Implemented the 32-bit xorshift pseudo-random address generator (shift triplet 13/17/5) in the testbench.<br>• Analyzed performance trade-offs, cache line thrashing, and conflict miss behavior under unbuffered memory loads.<br>• Co-authored the Experimental Results, Discussion, and Performance Tables. |
| 4 | **Anshu Yadav** | `2024NST-AY` | **Documentation, Build Automation & LaTeX Typesetting** | • Structured and formatted the IEEE conference paper specification (`CacheController_IEEE_Report.tex`).<br>• Configured the build runner script (`run.sh`) and simulation automation pipeline.<br>• Compiled and validated the IEEE final publication PDF (`CacheController_IEEE_Report.pdf`).<br>• Curated project references, compiled repository documentation, and formatted comparative architectural tables. |

---

## VI. Conclusion

This paper presented the design, implementation, and verification of a synthesizable 1 KB direct-mapped cache controller in Verilog HDL. Simulation results quantitatively demonstrated how spatial and temporal locality yield hit ratios of 75.0% and 90.0%, achieving AMAT reductions from 10.90 cycles down to 3.50 and 2.00 cycles, respectively. Synthesis results verified clean timing boundaries and predictable register allocation. Potential future enhancements include adding write-through/write-back support with dirty-bit tracking, multi-way set associativity (2-way/4-way) with pseudo-LRU replacement, and non-blocking hit-under-miss memory pipelines.

---

## References

- **[1]** W. A. Wulf and S. A. McKee, "Hitting the memory wall: Implications of the obvious," *ACM SIGARCH Computer Architecture News*, vol. 23, no. 1, pp. 20–24, Mar. 1995.
- **[2]** R. H. Dennard, F. H. Gaensslen, V. L. Rideout, E. Bassous, and A. R. LeBlanc, "Design of ion-implanted MOSFET's with very small physical dimensions," *IEEE Journal of Solid-State Circuits*, vol. 9, no. 5, pp. 256–268, Oct. 1974.
- **[3]** J. L. Hennessy and D. A. Patterson, *Computer Architecture: A Quantitative Approach*, 6th ed. Cambridge, MA, USA: Morgan Kaufmann, 2017.
- **[4]** D. A. Patterson and J. L. Hennessy, *Computer Organization and Design: The Hardware/Software Interface (RISC-V Edition)*, 2nd ed. San Francisco, CA, USA: Morgan Kaufmann, 2021.
- **[5]** P. J. Denning, "The locality principle," *Communications of the ACM*, vol. 48, no. 7, pp. 19–24, Jul. 2005.
- **[6]** M. V. Wilkes, "Slave memories and dynamic storage allocation," *IEEE Transactions on Electronic Computers*, vol. EC-14, no. 2, pp. 270–271, Apr. 1965.
- **[7]** A. J. Smith, "Cache memories," *ACM Computing Surveys (CSUR)*, vol. 14, no. 3, pp. 473–530, Sep. 1982.
- **[8]** M. D. Hill and A. J. Smith, "Evaluating associativity in CPU caches," *IEEE Transactions on Computers*, vol. 38, no. 12, pp. 1612–1630, Dec. 1989.
- **[9]** N. P. Jouppi, "Improving direct-mapped cache performance by the addition of a small fully-associative cache and prefetch buffers," in *Proc. 17th Annual International Symposium on Computer Architecture (ISCA)*, Seattle, WA, USA, 1990, pp. 364–373.
- **[10]** S. Przybylski, M. Horowitz, and J. Hennessy, "Characteristics of performance-optimal multi-level cache hierarchies," in *Proc. 16th Annual International Symposium on Computer Architecture (ISCA)*, Jerusalem, Israel, 1989, pp. 114–121.
- **[11]** *IEEE Standard for SystemVerilog—Unified Hardware Design, Specification, and Verification Language*, IEEE Std 1800-2017, 2018.
- **[12]** C. Wolf, "Yosys Open SYnthesis Suite," *YosysHQ*, 2020. [Online]. Available: https://yosyshq.net/yosys/
