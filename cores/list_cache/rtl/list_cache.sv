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
    input wire [DBW-1:0] S0_AXIS_TDATA,
    input wire           S0_AXIS_TVALID,
    output wire          S0_AXIS_TREADY,

    /* verilator lint_off UNUSEDSIGNAL */
    /* verilator lint_off UNDRIVEN */
    //// Unused
    input wire [3:0]     S0_AXIS_TDEST,
    input wire [7:0]     S0_AXIS_TID,
    input wire           S0_AXIS_TLAST,
    input wire [DBW-1:0] S0_AXIS_TUSER,
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
   reg                  cacheline_updated;

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

   assign S0_AXIS_TREADY = S0_AXIS_TVALID & (cacheline_needs_update | ~cacheline_updated);

   // Cacheline Refresh mech
   always @(posedge ACLK)
     if (reset_active) begin
        cacheline <= 0;
        cacheline_updated <= 0;
     end
     else begin // ~reset_active
        if (S0_AXIS_TVALID) begin
           if (S0_AXIS_TREADY) begin
              if (cacheline_needs_update) begin
                 cacheline <= S0_AXIS_TDATA;
                 cacheline_updated <= 1;
              end
              else begin // ~cacheline_needs_update
                 if (~cacheline_updated) begin
                    cacheline <= S0_AXIS_TDATA;
                    cacheline_updated <= 1;
                 end
              end
           end
           else begin // ~S0_AXIS_TREADY
              if (cacheline_needs_update) begin
                 cacheline <= S0_AXIS_TDATA;
                 cacheline_updated <= 1;
              end
              else begin // ~cacheline_needs_update
                 if (~cacheline_updated) begin
                    cacheline <= S0_AXIS_TDATA;
                    cacheline_updated <= 1;
                 end
              end
           end
        end
        else begin // ~S0_AXIS_TVALID
           if (cacheline_needs_update & cacheline_updated) cacheline_updated <= 0;
        end // else: !if(S0_AXIS_TVALID)
     end // else: !if(reset_active)




   // Cache fill Mech
   always @(posedge ACLK)
     if (reset_active) begin
        fetch_hand <= 0;
        cache_dirty <= 0;
        cache_total_uninit <= BS;
        cacheline_needs_update <= 1;
     end
     else if (cache_init) begin
        if (cache_dirty) begin
          cacheline_needs_update <= 1;
          if (cacheline_updated) begin
             cache[fetch_hand] <= cacheline;
             fetch_hand <= fetch_hand + 1;
             cache_dirty <= 0;
          end
        end
        else // ~cache_dirty
          cacheline_needs_update <= 0;
     end
     else begin // ~cache_init
        if (cacheline_updated) begin
           cache_total_uninit <= cache_total_uninit - 1;
           cache[fetch_hand] <= cacheline[FS-1:0];
           fetch_hand <= fetch_hand + 1;
           if (cache_total_uninit == 1) cacheline_needs_update <= 0;
           else                         cacheline_needs_update <= 1;
        end
        else
          cacheline_needs_update <= 1;
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
