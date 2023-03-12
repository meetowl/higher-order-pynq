#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "hls_stream.h"
#include "ap_axi_sdata.h"

// Register space
//------------------------------
// config/debug space
#define SIGNATURE 0
#define CEP_ADDR 1
#define CALL_COUNT 2
#define CURRENT_REP_ADDR 3
#define STATUS 4
#define ACCUMULATOR 5
#define DONE 6

// Endpoint to argument's space
#define CEP 8

// Data channel
#define REP_addr 10

// debug flags
#define IDLE 1
#define PROCESSING_LIST 2

#define DW 32
typedef ap_uint<DW> tpkt;

void add_reduce_ppo(volatile int *m_itf,
		volatile uint32_t regspace[16],
		hls::stream<tpkt> &list_in) {
#pragma HLS INTERFACE s_axilite port=regspace bundle=cep
#pragma HLS INTERFACE s_axilite port=return bundle=cep
#pragma HLS INTERFACE mode=m_axi depth=1 port=m_itf bundle=mst
#pragma HLS INTERFACE axis port=list_in

        regspace[STATUS] = IDLE;
	regspace[SIGNATURE] = 10101;

        tpkt next;
        uint32_t accumulator = 0;
        while (!regspace[REP_addr]) {
                if (list_in.read_nb(next)) {
                        accumulator += next;
                }
  tt      }

        /* Push the result back to the REP */
        m_itf = (volatile int*)regspace[REP_addr];
        *m_itf = accumulator;
        m_itf = (volatile int*)(regspace[REP_addr] + 4);
        *m_itf = 1;

        regspace[ACCUMULATOR] = 0;
        regspace[REP_addr] = 0;

        return;
}
