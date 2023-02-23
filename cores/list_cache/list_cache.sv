module list_cache
  #(
    parameter DW = 32
    )
   (
    // System
    input wire                CLK,
    input wire                RESET,

    // I/O
    input wire [FS-1:0][DW-1:0] IN,
    output reg [DW-1:0]       OUT,

    // Skid buffer signals
    input wire                i_valid,
    output wire               o_ready,

    output wire               o_valid,
    input wire                i_ready
    );

   // Buffer Size
   localparam           BS = 2;
   // Fetch Size
   localparam           FS = 4;
   // Hand Size
   // Must be:
   // - Big enough to address BS
   // - Small enough to overflow nicely
   localparam           HS = 3;

   // Registered Input
   /* verilator lint_off UNUSEDSIGNAL */
   reg [FS-1:0][DW-1:0] IN_R;

   // Caching
   reg [BS-1:0][FS-2:0][DW-1:0] cache;
   reg [HS-1:0]                 hand;
   reg                          fetch_hand;
   /* verilator lint_on UNUSEDSIGNAL */

   wire [((FS-1)*BS)-1:0][DW-1:0]   cache_read;
   assign cache_read = cache;


   // Skid Buffer part
   // Registers (r_)
   reg                          r_valid;
   // reg [DW-1:0]                 r_data;
   reg                          ro_valid;

   // Packet change detector
   wire                         packet_changed;

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
          OUT <= cache_read[hand];
       end

   assign packet_changed = ~(~IN[0][0] & ~IN_R[0][0]);

   // Packet change detector
   always @(posedge CLK)
     if (RESET)
        IN_R <= 1;
     else
       if (packet_changed) begin
          IN_R <= IN;
       end

   // Prefetch Mech
   always @(posedge CLK)
     if (RESET) begin
        cache <= 0;
        fetch_hand <= 0;
     end
     else
       if (packet_changed) begin
          cache[fetch_hand] <= IN[FS-1:1];
          fetch_hand <= fetch_hand + 1;
       end

   // Hand
   always @(posedge CLK)
     if (RESET)
       hand <= 0;
     else
       if (hand == ((FS-1) * BS) - 1)
         hand <= 0;
       else
         hand <= hand + 1;





   initial begin
      if ($test$plusargs("trace") != 0) begin
         $display("[%0t] Tracing to wavedump.vcd...\n", $time);
         $dumpfile("wavedump.vcd");
         $dumpvars();
      end
      $display("[%0t] Model running...\n", $time);
   end
endmodule
