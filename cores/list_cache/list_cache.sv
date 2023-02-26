module list_cache
  #(
    parameter DW = 32
    )
   (
    /* verilator lint_off UNUSEDSIGNAL */
    /* verilator lint_off UNDRIVEN */
    // System
    input wire                  CLK,
    input wire                  RESET,

    // I/O
    input wire [FS-1:0][DW-1:0] IN,
    output reg [DW-1:0]         OUT,

    // Skid buffer signals
    input wire                  i_valid,
    output wire                 next_ready,

    output wire                 o_valid,
    input wire                  i_ready
    /* verilator lint_on UNUSEDSIGNAL */
    /* verilator lint_on UNDRIVEN */
    );

   // Buffer Size
   localparam           BS = 2;
   // Fetch Size
   localparam           FS = 8;
   // Transfer size (how much data is actually transferred, TS * BS = len(list_cache))
   localparam           TS = FS - 1;
   // Hand Size
   localparam           HS = 5;

   // Registered Input
   /* verilator lint_off UNUSEDSIGNAL */
   reg [FS-1:0][DW-1:0] cacheline;

   // Caching
   reg [BS-1:0][TS-1:0][DW-1:0] cache;
   reg [HS-1:0]                 hand;
   /* verilator lint_on UNUSEDSIGNAL */

   wire [(TS*BS)-1:0][DW-1:0]   cache_read;
   assign cache_read = cache;

   // Prefetching
   reg                          fetch_hand;
   reg                          cache_dirty;
   reg                          cache_init;
   reg [1:0]                    cache_total_uninit;

   // Skid Buffer part
   // Registers (r_)
   // reg                          r_valid;
   // // reg [DW-1:0]                 r_data;
   // reg                          ro_valid;

   // Packet change detector
   wire                         packet_clock;
   wire                         cacheline_clock;
   wire                         refresh_ready;
   reg                          cacheline_changed;
   reg                          cacheline_last_clock;
   // o_data

   always @(posedge CLK)
     if (RESET)
       OUT <= 0;
     else if (!o_valid || i_ready)
       begin
          OUT <= cache_read[hand];
       end

   // We reserve the 0th bit as a 'clock' signal, indicator of sequence
   assign packet_clock = IN[0][0];
   assign cacheline_clock = cacheline[0][0];
   assign refresh_ready = packet_clock ^ cacheline_clock;
   assign cacheline_changed  = cacheline_last_clock ^ cacheline_clock;
   assign cache_init = cache_total_uninit == 0;

   // Refresh mech
   // The cacheline is refreshed, and then we get the next input ready
   always @(posedge CLK)
     if (RESET) begin
        cacheline <= 1;
        next_ready <= 0;
     end
     else
       if (i_valid & refresh_ready & ~cacheline_changed) begin
          cacheline <= IN;
          next_ready <= 1;
       end
       else if (next_ready & i_valid)
         next_ready <= 0;

   // Cacheline Mech
   always @(posedge CLK)
     if (RESET) begin
        cache <= 0;
        fetch_hand <= 0;
        cache_dirty <= 0;
        cache_total_uninit <= BS;
     end
     else
       if (cacheline_changed & (cache_dirty | ~cache_init)) begin
          cache[fetch_hand] <= cacheline[FS-1:1];
          fetch_hand <= fetch_hand + 1;
          cache_dirty <= 0;
          cacheline_last_clock <= cacheline_clock;
          if (~cache_init)
            cache_total_uninit <= cache_total_uninit - 1;
       end

   assign o_valid = cache_init;

   // Hand
   reg [HS-1:0] i;
   always @(posedge CLK)
     if (RESET | ~cache_init)
        hand <= 0;
     else
       if (hand == ((FS-1) * BS) - 1)
         hand <= 0;
       else begin
         for (i = 1; i <= BS; i++)
           if (hand == ((TS * i) - 1) - 1) begin
              cache_dirty <= 1;
           end
          hand <= hand + 1;
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
