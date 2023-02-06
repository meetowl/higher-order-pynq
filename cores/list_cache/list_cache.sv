module list_cache
  #(
    parameter TYPE_WIDTH = 32
    )
   (
    // System
    input wire                  CLK,
    input wire                  RESET,

    // HP Port
    //input wire [TYPE_WIDTH-1:0] LIST_IN,
    //output wire                 NEXT,

    // IP
    input wire                  READY,
    output reg [TYPE_WIDTH-1:0] ARG_OUT
    );

   localparam                    BT = TYPE_WIDTH - 1;
   //localparam                    TRUE = 1'b1;
   //localparam                    FALSE = 1'b0;

   reg [1:0][BT:0]               scratchpad;
   reg                           hand;

   always @(posedge CLK) begin
      if (~RESET) begin
         if (READY)
           ARG_OUT <= scratchpad[hand];
         if (~READY)
           hand <= hand + 1'b1;
      end
   end

   always @(posedge CLK) begin
      scratchpad[0] <= 1;
      scratchpad[1] <= 2;
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
