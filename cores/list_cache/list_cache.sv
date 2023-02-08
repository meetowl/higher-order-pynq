module list_cache
  #(
    parameter TYPE_WIDTH = 32
    )
   (
    // System
    input wire                  CLK,
    input wire                  RESET,
    input wire                  s_axi_control,

    // HP Port
    input wire [TYPE_WIDTH-1:0] LIST_IN,

    // DMA
    input wire                  LIST_NEXT_READY,

    // IP
    input wire                  ARG_RECEIVED,
    output reg [TYPE_WIDTH-1:0] ARG_OUT
    );

   localparam                   BUFFER_SIZE = 4;
   localparam                   HAND_SIZE = 3;
   localparam                   WIDTH_MAX = TYPE_WIDTH - 1;
   localparam                   BUF_MAX = BUFFER_SIZE - 1;
   localparam                   HAND_MAX = HAND_SIZE - 1;

   // localparam                    TRUE = 1'b1;
   // localparam                    FALSE = 1'b0;

   reg [BUF_MAX:0][WIDTH_MAX:0] scratchpad;
   reg [HAND_MAX:0]             hand;
   reg [HAND_MAX:0]             fetch_hand;

   assign fetch_hand = hand - 1'd1;

   always @(posedge CLK) begin
      if (~RESET)
        if (LIST_NEXT_READY) begin
           scratchpad[fetch_hand] <= LIST_IN;
        end
        else
          scratchpad[fetch_hand] <= scratchpad[fetch_hand];
   end

   always @(posedge CLK) begin
      if (~RESET)
        if (ARG_RECEIVED) begin
           ARG_OUT <= scratchpad[hand];
           hand <= hand;
        end
        else
          hand <= hand + 1;
   end

   always @(posedge CLK) begin
      if (RESET) begin
         hand <= 0;
      end
   end

   initial begin
      if ($test$plusargs("trace") != 0) begin
         $display("[%0t] Tracing to wavedump.vcd...\n", $time);
         $dumpfile("wavedump.vcd");
         $dumpvars();
      end
      $display("[%0t] Model running...\n", $time);
   end

endmodule
