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
#define CEP_a 8
#define CEP_b 9
#define REP_addr 10

// return-endpoint space
#define VAL_a 11
#define REP_a 12
#define VAL_b 13
#define REP_b 14

// debug flags
#define IDLE 0
#define WAITING_4_A 1
#define WAITING_4_B 2


//void adder_ppo(volatile int *m_itf, volatile uint32_t cep_a_addr, volatile uint32_t cep_b_addr, volatile uint32_t rep_addr, uint32_t regspace[16]){
void adder_ppo(volatile int *m_itf, volatile uint32_t regspace[16]){
	// set the native interface types
	#pragma HLS INTERFACE s_axilite port=regspace bundle=cep
	#pragma HLS INTERFACE s_axilite port=return bundle=cep

	// Removed offset=off
	#pragma HLS INTERFACE mode=m_axi depth=1 port=m_itf bundle=mst

	regspace[STATUS] = IDLE;
	regspace[SIGNATURE] = 22224;

	if(regspace[REP_addr] != 0) {
		regspace[CURRENT_REP_ADDR] = regspace[REP_addr];

		volatile uint32_t rep_a_addr = regspace[CEP_ADDR] + (VAL_a*0x4);
		volatile uint32_t rep_b_addr = regspace[CEP_ADDR] + (VAL_b*0x4);

		// Call the A exp
		//memcpy(&rep_a_addr, (uint64_t *)cep_a_addr, sizeof(uint32_t));
		m_itf = (volatile int*)regspace[CEP_a];
		*m_itf = rep_a_addr;
		regspace[STATUS] = WAITING_4_A;
		volatile uint32_t rep_a = regspace[REP_a];
		while(rep_a == 0) { rep_a = regspace[REP_a]; }

		// Call the B exp
		//memcpy(&rep_b_addr, (uint64_t *)cep_b_addr, sizeof(uint32_t));
		m_itf = (volatile int*)regspace[CEP_b];
		*m_itf = rep_b_addr;
		regspace[STATUS] = WAITING_4_B;
		volatile uint32_t rep_b = regspace[REP_b];
		while(rep_b == 0) { rep_b = regspace[REP_b]; }

		volatile uint32_t res = regspace[VAL_a] + regspace[VAL_b];
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
		regspace[REP_a] = 0;
		regspace[REP_b] =0;
	}
	return;
}
