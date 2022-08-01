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
#define REP_addr 10

// debug flags
#define IDLE 0
#define WAITING_4_A 1
#define WAITING_4_B 2


//void adder_ppo(volatile int *m_itf, volatile uint32_t cep_a_addr, volatile uint32_t cep_b_addr, volatile uint32_t rep_addr, uint32_t regspace[16]){
void a_top(volatile int *m_itf, volatile uint32_t regspace[16]){
	// set the native interface types

        // Our value input
	#pragma HLS INTERFACE s_axilite port=regspace bundle=cep
        // Our value output
	#pragma HLS INTERFACE s_axilite port=return bundle=cep

        // Our DMA
	#pragma HLS INTERFACE mode=m_axi depth=1 port=m_itf bundle=mst offset=off

	regspace[STATUS] = IDLE;
	regspace[SIGNATURE] = 99999;

	if(regspace[REP_addr] != 0) {
		regspace[CURRENT_REP_ADDR] = regspace[REP_addr];

		volatile uint32_t res = 1337;
		uint32_t rep_payload[2];
		rep_payload[0] = res;
		rep_payload[1] = regspace[CEP_ADDR];

		/* Push the result back to the REP */
		//memcpy(&rep_payload, (uint64_t *)rep_addr, sizeof(rep_payload));
		m_itf = (volatile int*)regspace[REP_addr];
		*m_itf = rep_payload[0];
		m_itf = (volatile int*)(regspace[REP_addr] + 4);
		*m_itf = rep_payload[1];

		/* clear the REP space */
		regspace[CALL_COUNT]++;
		regspace[REP_addr] = 0;
	}
	return;
}
