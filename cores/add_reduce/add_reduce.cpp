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
#define DEBUG 3
#define STATUS 4

// List's CEP Caller Ready address
#define LIST_CREADY 8

// Data channel
#define REP_ADDR 10

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
        regspace[DEBUG] = 22;
        uint32_t accumulator = 0;

        if (regspace[LIST_CREADY] && regspace[REP_ADDR]) {
                regspace[STATUS] = 2;
                while (!list_in.empty() || regspace[LIST_CREADY]) {
#pragma HLS PIPELINE II=1
                        tpkt t = 0;
                        if (list_in.read_nb(t)) {
                                accumulator += t;
                        }
                }
                regspace[STATUS] = 3;
                /* Push the result back to the REP */
                m_itf = (volatile int*)regspace[REP_ADDR];
                *m_itf = accumulator;
                m_itf = (volatile int*)(regspace[REP_ADDR] + 4);
                *m_itf = 1;

                regspace[REP_ADDR] = 0;
                accumulator = 0;
                regspace[DEBUG] = regspace[DEBUG] + 1;
        }

        return;
}
