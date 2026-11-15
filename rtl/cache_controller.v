// =====================================================================
// cache_controller.v - Direct-mapped, read-only cache + controller FSM
// =====================================================================
// Contains:
//   * Address Decoder   (tag / index / offset split)
//   * Tag RAM           (64 x 22-bit)
//   * Valid-Bit RAM     (64 x 1-bit)
//   * Cache Data RAM     (64 x 128-bit)
//   * Tag Comparator
//   * Controller FSM     (IDLE -> COMPARE -> HIT | ALLOCATE -> IDLE)
//   * Main-Memory Interface handshake
//   * Hit/miss counters
//
// CPU interface:
//   cpu_req   : pulse to request a read of cpu_addr
//   cpu_ready : pulse high when cpu_rdata holds the requested 32-bit word
// =====================================================================
`include "cache_defs.vh"

module cache_controller (
    input  wire                     clk,
    input  wire                     rst_n,

    // ---- CPU side ----
    input  wire                     cpu_req,
    input  wire [`ADDR_WIDTH-1:0]   cpu_addr,
    output reg                      cpu_ready,
    output reg  [31:0]              cpu_rdata,
    output reg                      hit_flag,     // 1 = this access was a hit (valid with cpu_ready)

    // ---- Main memory side ----
    output reg                      mem_req,
    output reg  [`ADDR_WIDTH-1:0]   mem_addr,
    input  wire                     mem_ready,
    input  wire [`BLOCK_BITS-1:0]   mem_rdata,

    // ---- Statistics (read by testbench) ----
    output reg  [31:0]              stat_accesses,
    output reg  [31:0]              stat_hits,
    output reg  [31:0]              stat_misses
);

    // ----------------------------------------------------------------
    // Cache storage
    // ----------------------------------------------------------------
    reg [`TAG_BITS-1:0]   tag_ram   [0:`NUM_LINES-1];
    reg                   valid_ram [0:`NUM_LINES-1];
    reg [`BLOCK_BITS-1:0] data_ram  [0:`NUM_LINES-1];

    // ----------------------------------------------------------------
    // Address Decoder
    // ----------------------------------------------------------------
    wire [`TAG_BITS-1:0]    addr_tag    = cpu_addr[`TAG_RANGE];
    wire [`INDEX_BITS-1:0]  addr_index  = cpu_addr[`INDEX_RANGE];
    wire [`OFFSET_BITS-1:0] addr_offset = cpu_addr[`OFFSET_RANGE];

    // Latch the request so the address is stable through the FSM
    reg [`TAG_BITS-1:0]    req_tag;
    reg [`INDEX_BITS-1:0]  req_index;
    reg [`OFFSET_BITS-1:0] req_offset;
    reg [`ADDR_WIDTH-1:0]  req_addr;

    // ----------------------------------------------------------------
    // Tag Comparator (combinational, on the latched request)
    // ----------------------------------------------------------------
    wire line_valid = valid_ram[req_index];
    wire tag_match  = (tag_ram[req_index] == req_tag);
    wire is_hit     = line_valid && tag_match;

    // Word select: pick the 32-bit word inside the 128-bit block.
    // offset[3:2] chooses one of 4 words (offset[1:0] = byte-in-word, ignored).
    wire [1:0] word_sel = req_offset[3:2];

    function [31:0] select_word;
        input [`BLOCK_BITS-1:0] block;
        input [1:0]             sel;
        begin
            case (sel)
                2'd0: select_word = block[ 31:  0];
                2'd1: select_word = block[ 63: 32];
                2'd2: select_word = block[ 95: 64];
                2'd3: select_word = block[127: 96];
            endcase
        end
    endfunction

    // ----------------------------------------------------------------
    // Controller FSM
    // ----------------------------------------------------------------
    localparam S_IDLE     = 2'd0;
    localparam S_COMPARE  = 2'd1;
    localparam S_ALLOCATE = 2'd2;   // wait for main memory, then refill
    localparam S_DONE     = 2'd3;

    reg [1:0] state;

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state         <= S_IDLE;
            cpu_ready     <= 1'b0;
            cpu_rdata     <= 32'd0;
            hit_flag      <= 1'b0;
            mem_req       <= 1'b0;
            mem_addr      <= {`ADDR_WIDTH{1'b0}};
            stat_accesses <= 32'd0;
            stat_hits     <= 32'd0;
            stat_misses   <= 32'd0;
            for (i = 0; i < `NUM_LINES; i = i + 1) begin
                valid_ram[i] <= 1'b0;
                tag_ram[i]   <= {`TAG_BITS{1'b0}};
            end
        end else begin
            // defaults (single-cycle pulses)
            cpu_ready <= 1'b0;
            hit_flag  <= 1'b0;
            mem_req   <= 1'b0;

            case (state)
            // ------------------------------------------------------
            S_IDLE: begin
                if (cpu_req) begin
                    // latch the request fields
                    req_tag    <= addr_tag;
                    req_index  <= addr_index;
                    req_offset <= addr_offset;
                    req_addr   <= cpu_addr;
                    stat_accesses <= stat_accesses + 32'd1;
                    state      <= S_COMPARE;
                end
            end

            // ------------------------------------------------------
            S_COMPARE: begin
                if (is_hit) begin
                    stat_hits <= stat_hits + 32'd1;
                    cpu_rdata <= select_word(data_ram[req_index], word_sel);
                    cpu_ready <= 1'b1;
                    hit_flag  <= 1'b1;
                    state     <= S_IDLE;
                end else begin
                    // MISS: kick off main-memory fetch of the block
                    stat_misses <= stat_misses + 32'd1;
                    mem_addr    <= req_addr;
                    mem_req     <= 1'b1;
                    state       <= S_ALLOCATE;
                end
            end

            // ------------------------------------------------------
            S_ALLOCATE: begin
                // hold mem_req low (pulsed already); wait for memory
                if (mem_ready) begin
                    // Refill the line: write data, tag, set valid
                    data_ram[req_index]  <= mem_rdata;
                    tag_ram[req_index]   <= req_tag;
                    valid_ram[req_index] <= 1'b1;
                    // Return the requested word to the CPU
                    cpu_rdata <= select_word(mem_rdata, word_sel);
                    cpu_ready <= 1'b1;
                    hit_flag  <= 1'b0;      // it was a miss
                    state     <= S_IDLE;
                end
            end

            default: state <= S_IDLE;
            endcase
        end
    end

endmodule
