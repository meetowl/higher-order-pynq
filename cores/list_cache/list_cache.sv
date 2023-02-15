module list_cache
  #(
    parameter DW = 32
    )
   (
    // System
    input wire           CLK,
    input wire           RESET,

    input wire           i_valid,
    input wire [DW-1:0]  i_data,
    output wire          o_ready,


    output wire           o_valid,
    output reg [DW-1:0]  o_data,
    input wire          i_ready
    );

   // // Buffer Size
   // localparam                   BS = 4;
   // // Hand Size
   // // Must be:
   // // - Big enough to address BS
   // // - Small enough to overflow nicely
   // localparam                   HS = 3;

   // reg [BS-1:0][DW-1:0]         scratchpad;
   // reg [HS-1:0]                 hand;


   // Skid Buffer part
   // Registers (r_)
   reg                          r_valid;
   reg [DW-1:0]                 r_data;
   reg                          ro_valid;

   // r_valid
   // Only valid when we are ready to give output but input of next is stalled
   always @(posedge CLK)
     if (RESET)
       r_valid <= 0;
     else if ((i_valid && o_ready) && (o_valid && !i_ready))
       r_valid <= 1;
     else if (i_ready)
       r_valid <= 0;

   // r_data
   always @(posedge CLK)
     if (RESET)
       r_data <= 0;
     else if (o_ready)
       r_data <= i_data;

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
       o_data <= 0;
     else if (!o_valid || i_ready)
       begin
          if (r_valid)
            o_data <= r_data;
          else if (i_valid)
            o_data <= i_data;
          else
            o_data <= 0;
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
