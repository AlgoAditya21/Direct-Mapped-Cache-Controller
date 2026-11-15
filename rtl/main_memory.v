// =====================================================================
// main_memory.v - Behavioral main-memory model + interface
// =====================================================================
// Slow backing store. On a cache miss the controller asks for a whole
// 128-bit (16-byte) block. Latency is modelled by MEM_LATENCY cycles
// before 'ready' pulses high with the data.
//
// Data pattern is deterministic (derived from block address) so the
// testbench can self-check without loading a file.
// =====================================================================
`include "cache_defs.vh"

module main_memory #(
    parameter MEM_LATENCY = 10          // cycles to service one block fetch
)(
    input  wire                     clk,
    input  wire                     rst_n,

    input  wire                     req,        // controller asserts to start a fetch
    input  wire [`ADDR_WIDTH-1:0]   addr,       // byte address (block-aligned region used)
    output reg                      ready,      // 1-cycle pulse when data valid
    output reg  [`BLOCK_BITS-1:0]   rdata       // 128-bit block
);

    // Latency counter
    reg [7:0] cnt;
    reg       busy;

    // Block number = address with offset bits stripped
    wire [`ADDR_WIDTH-`OFFSET_BITS-1:0] block_num = addr[`ADDR_WIDTH-1:`OFFSET_BITS];

    // Deterministic "memory contents": each 32-bit word of the block is
    // block_num combined with the word index, so every block is unique.
    function [`BLOCK_BITS-1:0] gen_block;
        input [`ADDR_WIDTH-`OFFSET_BITS-1:0] bnum;
        reg [31:0] w0, w1, w2, w3;
        begin
            w0 = (bnum * 4) + 0;
            w1 = (bnum * 4) + 1;
            w2 = (bnum * 4) + 2;
            w3 = (bnum * 4) + 3;
            gen_block = { w3, w2, w1, w0 };   // word0 in low bits
        end
    endfunction

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cnt   <= 8'd0;
            busy  <= 1'b0;
            ready <= 1'b0;
            rdata <= {`BLOCK_BITS{1'b0}};
        end else begin
            ready <= 1'b0;                 // default: no pulse

            if (!busy && req) begin
                busy <= 1'b1;
                cnt  <= MEM_LATENCY[7:0];
            end else if (busy) begin
                if (cnt > 8'd1) begin
                    cnt <= cnt - 8'd1;
                end else begin
                    busy  <= 1'b0;
                    ready <= 1'b1;         // data ready this cycle
                    rdata <= gen_block(block_num);
                end
            end
        end
    end

endmodule
