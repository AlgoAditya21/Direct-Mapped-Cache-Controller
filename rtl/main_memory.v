// =====================================================================
// main_memory.v - Behavioral main-memory model and interface
// =====================================================================
`include "cache_defs.vh"

module main_memory #(
    parameter MEM_LATENCY = 10
)(
    input  wire                     clk,
    input  wire                     rst_n,

    input  wire                     req,
    input  wire [`ADDR_WIDTH-1:0]   addr,
    output reg                      ready,
    output reg  [`BLOCK_BITS-1:0]   rdata
);

    reg [7:0] cnt;
    reg       busy;

    wire [`ADDR_WIDTH-`OFFSET_BITS-1:0] block_num = addr[`ADDR_WIDTH-1:`OFFSET_BITS];

    function [`BLOCK_BITS-1:0] gen_block;
        input [`ADDR_WIDTH-`OFFSET_BITS-1:0] bnum;
        reg [31:0] w0, w1, w2, w3;
        begin
            w0 = (bnum * 32'd4) + 32'd0;
            w1 = (bnum * 32'd4) + 32'd1;
            w2 = (bnum * 32'd4) + 32'd2;
            w3 = (bnum * 32'd4) + 32'd3;
            gen_block = { w3, w2, w1, w0 };
        end
    endfunction

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cnt   <= 8'd0;
            busy  <= 1'b0;
            ready <= 1'b0;
            rdata <= {`BLOCK_BITS{1'b0}};
        end else begin
            ready <= 1'b0;

            if (!busy && req) begin
                busy <= 1'b1;
                cnt  <= MEM_LATENCY[7:0];
            end else if (busy) begin
                if (cnt > 8'd1) begin
                    cnt <= cnt - 8'd1;
                end else begin
                    busy  <= 1'b0;
                    ready <= 1'b1;
                    rdata <= gen_block(block_num);
                end
            end
        end
    end

endmodule
