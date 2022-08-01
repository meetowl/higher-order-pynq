#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>


// Register space
//------------------------------
// config/debug space
#define SIGNATURE 0
#define CEP_ADDR 1
#define CALL_COUNT 2
#define CURRENT_REP_ADDR 3
#define STATUS 4

// call-endpoint space
#define CEP_in 5
#define VAL_len 6
#define CEP_out 7
#define REP_addr 10

// return-endpoint space
#define VAL_in 11 // For the input
#define REP_in 12

#define REP_out 13 // for out

// debug flags
#define IDLE 0
#define WAITING_4_IN 1
#define WAITING_4_OUT 2


void accumulator(volatile int *m_itf, volatile uint32_t regspace[16]){
	// set the native interface types
	#pragma HLS INTERFACE s_axilite port=regspace bundle=cep
	#pragma HLS INTERFACE s_axilite port=return bundle=cep

	#pragma HLS INTERFACE mode=m_axi depth=1 port=m_itf bundle=mst offset=off

	regspace[STATUS] = IDLE;
	regspace[SIGNATURE] = 989898;

	volatile uint32_t acc_reg = 0; // the register that we are accumulating

	if(regspace[REP_addr] != 0) {
		regspace[CURRENT_REP_ADDR] = regspace[REP_addr];

		volatile uint32_t rep_in_addr = regspace[CEP_ADDR] + (VAL_in*0x4);
		volatile uint32_t rep_out_addr = regspace[CEP_ADDR] + (REP_out*0x4);

		for(int i=0; i<regspace[VAL_len]; i++) {
			// Call the in function
			m_itf = (volatile int*)regspace[CEP_in];
			*m_itf = rep_in_addr;
			regspace[STATUS] = WAITING_4_IN;
			volatile uint32_t rep_a = regspace[REP_in];
			while(rep_a == 0) { rep_a = regspace[REP_in]; }

			acc_reg = acc_reg + regspace[VAL_in];
		}


		// Call the out function
		uint32_t out_payload[2];
		out_payload[0] = acc_reg;
		out_payload[1] = rep_out_addr;
		m_itf = (volatile int*)regspace[CEP_out];
		*m_itf = out_payload[0];
		m_itf = (volatile int*)(regspace[CEP_out] + 4);
		*m_itf = out_payload[1];
		regspace[STATUS] = WAITING_4_OUT;
		volatile uint32_t rep_out = regspace[REP_out];
		while(rep_out == 0) { rep_out = regspace[REP_out]; }

		acc_reg = 0;

		/* Push the result back to the REP */
		m_itf = (volatile int*)regspace[REP_addr];
		*m_itf = regspace[CEP_out];

		/* clear the REP space */
		regspace[CALL_COUNT]++;
		regspace[REP_addr] = 0;
		regspace[REP_in] = 0;
		regspace[REP_out] =0;
	}
	return;
}
