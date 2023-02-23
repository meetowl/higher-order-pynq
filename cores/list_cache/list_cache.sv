module list_cache
  #(
    parameter DW = 32
    )
   (
    // System
    input wire                  CLK,
    input wire                  RESET,

    // I/O
    input wire [FS-1:0][DW-1:0] IN,
    output reg [DW-1:0]         OUT,

    // Skid buffer signals
    input wire                  i_valid,
    output wire                 o_ready,

    output wire                 o_valid,
    input wire                  i_ready
    );

   // Buffer Size
   // localparam           BS = 2;
   // Fetch Size
   localparam           FS = 4;
   // Hand Size
   // Must be:
   // - Big enough to address BS
   // - Small enough to overflow nicely
   // localparam           HS = 3;

   // Registered Input
   /* verilator lint_off UNUSEDSIGNAL */
   reg [FS-2:0][DW-1:0] IN_R;
   /* verilator lint_on UNUSEDSIGNAL */
   // Caching
   // reg [BS-1:0][FS-1:0][DW-1:0] cache;
   // reg [HS-1:0]                 hand;


   // Skid Buffer part
   // Registers (r_)
   reg                          r_valid;
   // reg [DW-1:0]                 r_data;
   reg                          ro_valid;

   // Packet change detector
   reg                          last_packet;

   // r_valid
   // Only valid when we are ready to give output but input of next is stalled
   always @(posedge CLK)
     if (RESET)
       r_valid <= 0;
     else if ((i_valid && o_ready) && (o_valid && !i_ready))
       r_valid <= 1;
     else if (i_ready)
       r_valid <= 0;

   assign o_ready = !r_valid;

   // ro_valid
   always @(posedge CLK)
     if (RESET)
       ro_valid <= 0;
     else if (!o_valid || i_ready)
       ro_valid <= (i_valid || r_valid);

   assign o_valid = ro_valid;

   // o_data
   always @(posedge CLK)
     if (RESET)
       OUT <= 0;
     else if (!o_valid || i_ready)
       begin
          if (r_valid)
            OUT <= IN_R[1];
          else if (i_valid)
            OUT <= IN[1];
          else
            OUT <= IN[1];
       end

   // Packet change detector
   always @(posedge CLK)
     if (RESET) begin
        // We always expect first packet to have signal 0
        last_packet <= 1;
        IN_R <= 0;
     end
     else
       if (~(IN[0][0] & last_packet)) begin
          last_packet <= IN[0][0];
          IN_R <= {IN[3], IN[2], IN[1]};
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
