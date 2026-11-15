// =====================================================================
// cache_defs.vh - Shared parameters for the direct-mapped cache
// =====================================================================
// Config: 1 KB cache, 16-byte blocks, 32-bit byte addresses
//
//   Cache size   = 1024 bytes
//   Block size   = 16 bytes      -> OFFSET = log2(16) = 4 bits
//   Num blocks   = 1024/16 = 64  -> INDEX  = log2(64) = 6 bits
//   Address      = 32 bits       -> TAG    = 32 - 6 - 4 = 22 bits
//
//   | 31 .......... 10 | 9 ..... 4 | 3 ..... 0 |
//   |     TAG (22)     | INDEX (6) | OFFSET(4) |
// =====================================================================
`ifndef CACHE_DEFS_VH
`define CACHE_DEFS_VH

`define ADDR_WIDTH   32
`define CACHE_SIZE   1024          // bytes
`define BLOCK_SIZE   16            // bytes per block

`define OFFSET_BITS  4             // log2(BLOCK_SIZE)
`define INDEX_BITS   6             // log2(CACHE_SIZE/BLOCK_SIZE)
`define TAG_BITS     22            // ADDR_WIDTH - INDEX_BITS - OFFSET_BITS

`define NUM_LINES    64            // CACHE_SIZE/BLOCK_SIZE
`define BLOCK_BITS   128           // BLOCK_SIZE * 8  (one line = 16 bytes = 128 bits)

// Field slices of a 32-bit address
`define OFFSET_RANGE  3:0
`define INDEX_RANGE   9:4
`define TAG_RANGE    31:10

`endif
