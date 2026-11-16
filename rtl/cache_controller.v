// =====================================================================
// cache_controller.v - Direct-mapped, read-only cache + controller FSM
// =====================================================================
`include "cache_defs.vh"

module cache_controller (
    input  wire                     clk,
    input  wire                     rst_n,

    // CPU interface
    input  wire                     cpu_req,
    input  wire [`ADDR_WIDTH-1:0]   cpu_addr,
    output reg                      cpu_ready,
    output reg  [31:0]              cpu_rdata,
    output reg                      hit_flag,

    // Main memory interface
    output reg                      mem_req,
    output reg  [`ADDR_WIDTH-1:0]   mem_addr,
    input  wire                     mem_ready,
    input  wire [`BLOCK_BITS-1:0]   mem_rdata,

    // Performance counters
    output reg  [31:0]              stat_accesses,
    output reg  [31:0]              stat_hits,
    output reg  [31:0]              stat_misses
);

    reg [`TAG_BITS-1:0]   tag_ram   [0:`NUM_LINES-1];
    reg                   valid_ram [0:`NUM_LINES-1];
    reg [`BLOCK_BITS-1:0] data_ram  [0:`NUM_LINES-1];

    wire [`TAG_BITS-1:0]    addr_tag    = cpu_addr[`TAG_RANGE];
    wire [`INDEX_BITS-1:0]  addr_index  = cpu_addr[`INDEX_RANGE];
    wire [`OFFSET_BITS-1:0] addr_offset = cpu_addr[`OFFSET_RANGE];

    reg [`TAG_BITS-1:0]    req_tag;
    reg [`INDEX_BITS-1:0]  req_index;
    reg [`OFFSET_BITS-1:0] req_offset;
    reg [`ADDR_WIDTH-1:0]  req_addr;

    wire line_valid = valid_ram[req_index];
    wire tag_match  = (tag_ram[req_index] == req_tag);
    wire is_hit     = line_valid && tag_match;

    wire [1:0] word_sel = req_offset[3:2];

    function [31:0] select_word;
        input [`BLOCK_BITS-1:0] block;
        input [1:0]             sel;
        begin
            case (sel)
                2'b00:   select_word = block[31:0];
                2'b01:   select_word = block[63:32];
                2'b10:   select_word = block[95:64];
                2'b11:   select_word = block[127:96];
                default: select_word = 32'h0000_0000;
            endcase
        end
    endfunction

    localparam [1:0] S_IDLE     = 2'b00,
                     S_COMPARE  = 2'b01,
                     S_ALLOCATE = 2'b10,
                     S_DONE     = 2'b11;

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
            cpu_ready <= 1'b0;
            hit_flag  <= 1'b0;
            mem_req   <= 1'b0;

            case (state)
            S_IDLE: begin
                if (cpu_req) begin
                    req_tag       <= addr_tag;
                    req_index     <= addr_index;
                    req_offset    <= addr_offset;
                    req_addr      <= cpu_addr;
                    stat_accesses <= stat_accesses + 32'd1;
                    state         <= S_COMPARE;
                end
            end

            S_COMPARE: begin
                if (is_hit) begin
                    stat_hits <= stat_hits + 32'd1;
                    cpu_rdata <= select_word(data_ram[req_index], word_sel);
                    cpu_ready <= 1'b1;
                    hit_flag  <= 1'b1;
                    state     <= S_IDLE;
                end else begin
                    stat_misses <= stat_misses + 32'd1;
                    mem_addr    <= req_addr;
                    mem_req     <= 1'b1;
                    state       <= S_ALLOCATE;
                end
            end

            S_ALLOCATE: begin
                if (mem_ready) begin
                    data_ram[req_index]  <= mem_rdata;
                    tag_ram[req_index]   <= req_tag;
                    valid_ram[req_index] <= 1'b1;
                    cpu_rdata            <= select_word(mem_rdata, word_sel);
                    cpu_ready            <= 1'b1;
                    hit_flag             <= 1'b0;
                    state                <= S_IDLE;
                end
            end

            default: state <= S_IDLE;
            endcase
        end
    end

endmodule
