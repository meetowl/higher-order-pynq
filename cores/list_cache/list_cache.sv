module list_cache
  #(
    // Data width (Bits)
    parameter DW = 32,
    // Data Bus Width (Bits)
    parameter DBW = 256
    )
   (

    // AXI4-Stream Communication
    input wire           ACLK,
    input wire           ARESETn,
    input wire [DBW-1:0] TDATA,
    input wire           TVALID,
    output reg           TREADY,

    /* verilator lint_off UNUSEDSIGNAL */
    /* verilator lint_off UNDRIVEN */
    //// Unused
    input wire [3:0]     TDEST,
    input wire [7:0]     TID,
    input wire           TLAST,
    input wire [DBW-1:0] TUSER,
    /* verilator lint_on UNUSEDSIGNAL */
    /* verilator lint_on UNDRIVEN */

    // HoP Module Communication
    input reg            I_READY,
    output reg [DW-1:0]  OUT,
    output reg           O_VALID

    );

   // Buffer Size
   localparam           BS = 2;
   // Fetch Size
   localparam           FS = DBW / DW;
   // Hand Size
   // CAREFUL: This needs to overflow nicely (avoid the logic for it)
   localparam           HS = $clog2(FS * BS);
   // TODO: Figure out how to do this properly
   // assert final ((2 ** HS) == ($clog2(FS * BS)));

   // Registered Input
   reg [FS-1:0][DW-1:0] cacheline;
   reg                  cacheline_needs_update;

   // Caching
   reg [BS-1:0][FS-1:0][DW-1:0] cache;
   reg [HS-1:0]                 hand;
   /// For comparisons, verilator trips with 2b == 3b
   /// so we answer its wishes by casting
   reg [HS + 4:0]                   hand_cmp;
   // assign hand_cmp = {{(32 - HS){1'b0}}, hand};
   assign hand_cmp = {{5'b0}, hand};


   // Make cache reading easier
   wire [(FS*BS)-1:0][DW-1:0]   cache_read;
   assign cache_read = cache;

   // Prefetching
   reg                          fetch_hand;
   reg                          cache_dirty;
   reg                          cache_init;
   reg [1:0]                    cache_total_uninit;
   reg                          cache_empty;

   // ARESETn is ACTIVE_LOW by default.
   wire                         reset_active;
   assign reset_active = ~ARESETn;

   // OUT
   // O_VALID is up if its correct so don't care about
   // non-nil values.
   always @(posedge ACLK)
     if (reset_active)
       OUT <= 0;
     else
       OUT <= cache_read[hand];

   assign cache_init = cache_total_uninit == 0;

   // Cacheline Refresh mech
   always @(posedge ACLK)
     if (reset_active) begin
        cacheline <= 0;
        cacheline_needs_update <= 1;
        TREADY <= 0;
     end
     else if (cache_init) begin
       if (TVALID & cacheline_needs_update) begin
          cacheline <= TDATA;
          cacheline_needs_update <= 0;
          TREADY <= 1;
       end
       else if (TREADY & TVALID)
         TREADY <= 0;
     end
     else begin // cache_init == 0
        if (TVALID & cacheline_needs_update) begin
           cacheline <= TDATA;
           cacheline_needs_update <= 0;
           TREADY <= 1;
        end
        else if (TVALID & TREADY)
          TREADY <= 0;


     end

   // Cache fill Mech
   always @(posedge ACLK)
     if (reset_active) begin
        fetch_hand <= 0;
        cache_dirty <= 0;
        cache_total_uninit <= BS;
     end
     else if (cache_init) begin
       if (cache_dirty & ~cacheline_needs_update) begin
          cache[fetch_hand] <= cacheline;
          cacheline_needs_update <= 1;
          fetch_hand <= fetch_hand + 1;
          cache_dirty <= 0;
       end
     end
     else begin // cache_init == 0
        if (~cacheline_needs_update) begin
           cache_total_uninit <= cache_total_uninit - 1;
           cacheline_needs_update <= 1;
           cache[fetch_hand] <= cacheline[FS-1:0];
           fetch_hand <= fetch_hand + 1;
        end
     end

   // cache_empty
   assign cache_empty = (hand_cmp == (fetch_hand * FS)) & cache_dirty;

   // Hand
   reg [HS-1:0] i;
   always @(posedge ACLK)
     if (reset_active | ~cache_init) begin
        hand <= 0;
        O_VALID <= 0;
     end
     else if (~cache_empty & cache_init & I_READY) begin
        O_VALID <= 1;
        for (i = 1; i <= BS; i++)
          if (hand_cmp == ((FS * i) - 1) - 1) begin
             cache_dirty <= 1;
          end
        hand <= hand + 1;
     end
     else if (~I_READY & cache_init) begin
        O_VALID <= 1;
        hand <= hand;
     end
     else if (cache_empty | ~cache_init) begin
        hand <= hand;
        O_VALID <= 0;
     end


   initial begin
      if ($test$plusargs("trace") != 0) begin
         $display("[%0t] Tracing to wavedump.vcd...\n", $time);
         $dumpfile("wavedump.vcd");
         $dumpvars();
      end
      $display("[%0t] Model running...\n", $time);
      $display("[%0t] BS:%d, FS:%d, HS:%d\n", $time, BS, FS, HS);
   end
endmodule
