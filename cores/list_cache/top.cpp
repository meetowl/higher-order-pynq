#include <vector>
#include <iostream>
#include <list>
#include "verilated.h"
#include "Vlist_cache.h"

#define FETCH_SIZE 8
#define PACKET_START 1

int *clock_time;
int correct_out;

inline void increment_eval(std::shared_ptr<VerilatedContext> contextp,
                    std::shared_ptr<Vlist_cache> top) {
        for (int i = 0; i < 2; i++) {
                contextp->timeInc(1);
                top->CLK = !top->CLK;
                top->eval();
                if (top->CLK) { // Rising edge
                        if (top->o_valid && top->i_ready) {
                                if (top->OUT != correct_out) {
                                        printf("error: [%d] Expected %d but got %d.\n", *clock_time,
                                               correct_out, top->OUT);
                                }
                                ++correct_out;
                        }
                        ++(*clock_time);
                }
        }
}

int main(int argc, char** argv, char** env) {
        int ct = 0;
        clock_time = &ct;
        int fetch_size = 8;
        int data_size = fetch_size - 1;
        int list_size = data_size * 16;
        // Prevent unused variable warnings
        if (false && argc && argv && env) {}

        const std::shared_ptr<VerilatedContext> contextp{new VerilatedContext};
        Verilated::traceEverOn(true);
        contextp->debug(0);
        contextp->randReset(2);
        contextp->traceEverOn(true);
        contextp->commandArgs(argc, argv);
        const std::shared_ptr<Vlist_cache> top{new Vlist_cache{contextp.get(), "TOP"}};

        // Initialise the input list
        correct_out = PACKET_START;
        std::vector<int> xs = std::vector<int>(list_size);
        for (int i = 0; i < list_size; i++) xs[i] = correct_out + i;

        top->CLK = 0;
        top->RESET = 1;
        top->i_valid = 0;
        // Warm up
        for (int i = 0; i < 2; i++) {
                increment_eval(contextp, top);
        }
        top->RESET = 0;

        // Pin IP ready pin to ready
        top->i_ready = 1;


        int packets = xs.size() / data_size ;
        if (xs.size() % data_size != 0) ++packets;
        int last_packet = 0;
        // Process
        int i = 0;
        bool first = true;

        top->i_ready = 0;
        while (i < packets) {
                // Prepare packet
                int packet[fetch_size];
                packet[0] = last_packet;

                for (int j = 0; j < fetch_size - 1; j++) {
                        packet[j+1] = xs[(i * data_size) + j];
                        last_packet = !last_packet;
                }

                if (!first) {
                        while (ct >= 30 &&
                            ct <= 45) {
                                top->i_ready = 0;
                                increment_eval(contextp, top);
                        }
                        if (ct > 7) top->i_ready = 1;
                        while (!top->next_ready) increment_eval(contextp, top);
                }

                // Update wires
                printf("[");
                for (int j = 0; j < fetch_size; j++) {
                        printf("%d,", packet[j]);
                        top->IN[j] = packet[j];

                }
                printf("]\n");

                if (first) {
                        increment_eval(contextp, top);
                        top->i_valid = 1;
                        first = false;
                }
                ++i;
                increment_eval(contextp, top);
        }

        while (top->o_valid) increment_eval(contextp, top);
        top->final();
        return 0;
        }
