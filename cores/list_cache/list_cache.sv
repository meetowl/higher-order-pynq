module list_cache
  #(
    // Data width (Bits)
    parameter DW = 32,
    // Data Bus Width (Bits)
    parameter DBW = 4096
    )
   (
    /* verilator lint_off UNUSEDSIGNAL */
    /* verilator lint_off UNDRIVEN */

    // AXI4-Stream Communication
    input wire          ACLK,
    input wire          ARESETn,
    input wire [BDW:0]  TDATA,
    input wire          TVALID;
    output wire         TREADY;

    //// Unused
    input wire [3:0]    TDEST;
    input wire [7:0]    TID;
    input wire          TLAST;
    input wire [N-1:0]  TUSER;


    // HoP Module Communication
    input reg           I_READY
    output reg [DW-1:0] OUT,
    output reg          O_VALID,
    /* verilator lint_on UNUSEDSIGNAL */
    /* verilator lint_on UNDRIVEN */
    );

   // Buffer Size
   localparam           BS = 2;
   // Fetch Size
   localparam           FS = DBW / DW;
   // Hand Size
   localparam           HS = 5;

   // Registered Input
   reg [FS-1:0][DW-1:0] cacheline;

   // Caching
   reg [BS-1:0][TS-1:0][DW-1:0] cache;
   reg [HS-1:0]                 hand;

   // Make cache reading easier
   wire [(TS*BS)-1:0][DW-1:0]   cache_read;
   assign cache_read = cache;

   // Prefetching
   reg                          fetch_hand;
   reg                          cache_dirty;
   wire                         cache_init;
   reg [1:0]                    cache_total_uninit;
   wire                         cache_empty;

   // Packet change detector
   wire                         packet_clock;
   wire                         cacheline_clock;
   wire                         refresh_ready;
   reg                          cacheline_changed;
   reg                          cacheline_last_clock;

   // OUT
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
        cacheline <= 1;
        cacheline_last_clock <= 1;
     end
     else if (cache_init) begin
       if (cacheline_changed & cache_dirty) begin
          cache[fetch_hand] <= cacheline[FS-1:1];
          fetch_hand <= fetch_hand + 1;
          cache_dirty <= 0;
          cacheline_last_clock <= cacheline_clock;
       end
     end
     else // cache_init = 0
       if (cacheline_changed) begin
          cache_total_uninit <= cache_total_uninit - 1;
          fetch_hand <= fetch_hand + 1;
          cacheline_last_clock <= cacheline_clock;
          cache[fetch_hand] <= cacheline[FS-1:1];
       end

   assign cache_empty = (hand == fetch_hand * TS) & cache_dirty;

   // Hand
   reg [HS-1:0] i;
   always @(posedge CLK)
     if (RESET | ~cache_init) begin
        hand <= 0;
        o_valid <= 0;
     end
     else if (~cache_empty & i_ready) begin
        o_valid <= 1;
        if (hand == ((FS-1) * BS) - 1)
          hand <= 0;
        else begin
           for (i = 1; i <= BS; i++)
             if (hand == ((TS * i) - 1) - 1) begin
                cache_dirty <= 1;
             end
           hand <= hand + 1;
        end
     end // if (~cache_empty)
     else if (cache_empty) begin
        hand <= hand;
        o_valid <= 0;
     end
     else if (~i_ready) begin
        o_valid <= 1;
        hand <= hand;
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
