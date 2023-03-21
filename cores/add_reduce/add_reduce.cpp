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

// Reset signal for caller
#define RESET 5

// Endpoint to argument's space
#define CEP 8

// Data channel
#define REP_addr 10tt

// debug flags
#define IDLE 0
#define WAITING_FOR_REP_ADDR 1
#define PROCESSING_LIST 2


void add_reduce_ppo(volatile int *m_itf,
		volatile uint32_t regspace[16],
		hls::stream<ap_axis<32,2,5,6>> &list_in) {
#pragma HLS INTERFACE s_axilite port=regspace bundle=cep
#pragma HLS INTERFACE s_axilite port=return bundle=cep

	// Removed offset=off
#pragma HLS INTERFACE mode=m_axi depth=1 port=m_itf bundle=mst

	// Streaming interface
#pragma HLS INTERFACE axis port=list_in

	regspace[SIGNATURE] = 10101;
	ap_axis<32,2,5,6> num;
	if (regspace[RESET]) {
		regspace[STATUS] = IDLE;
		regspace[REP_addr] = 0;
	} else if ((volatile int*) regspace[REP_addr]) {
		regspace[STATUS] = WAITING_FOR_REP_ADDR;
	} else {
		regspace[STATUS] = PROCESSING_LIST;
		regspace[CURRENT_REP_ADDR] = regspace[REP_addr];

		// Tell the list stub we are ready to receive communicado
		m_itf = (volatile int*)regspace[CEP];
		*m_itf = 1;

		// Process the list
		while (!regspace[RESET]) {
			list_in.read(num);
			// Accumulate to existing result
			uint32_t res = regspace[REP_addr] + num.data;

			// immediate optimisation: don't write result to memory just keep it internal
			// like this for debugging
			uint32_t rep_payload[2];
			rep_payload[0] = res;
			rep_payload[1] = regspace[CEP_ADDR];

			/* Push the result back to the REP */
			m_itf = (volatile int*)regspace[REP_addr];
			*m_itf = rep_payload[0];
			m_itf = (volatile int*)(regspace[REP_addr] + 4);
			*m_itf = rep_payload[1];
		}
		regspace[CALL_COUNT]++;
	}
	return;
}
