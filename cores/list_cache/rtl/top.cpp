#include <vector>
#include <iostream>
#include <list>
#include "verilated.h"
#include "Vlist_cache.h"

#define PACKET_START 1
#define MAX_ITER 100

int *clock_time;
int correct_out;

inline void increment_eval(std::shared_ptr<VerilatedContext> contextp,
                    std::shared_ptr<Vlist_cache> top) {
        for (int i = 0; i < 2; i++) {
                contextp->timeInc(1);
                top->ACLK = !top->ACLK;
                top->eval();
                if (top->ACLK) { // Rising edge
                        if (top->O_VALID && top->I_READY) {
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
        constexpr int data_width = 32;
        constexpr int data_bus_width = 256;
        constexpr int fetch_size = data_bus_width / data_width;
        constexpr int list_size = fetch_size * 16;
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

        top->ACLK = 0;
        top->ARESETn = 0;
        top->S0_AXIS_TVALID = 0;
        // Warm up
        for (int i = 0; i < 2; i++) {
                increment_eval(contextp, top);
        }
        top->ARESETn = 1;

        // Pin IP ready pin to ready
        top->I_READY = 1;

        int packets = xs.size() / fetch_size ;
        if (xs.size() % fetch_size != 0) ++packets;
        // Process
        int i = 0;
        int iter = 0;
        bool first = true;

        top->I_READY = 1;
        while (i < packets && iter < MAX_ITER) {
                // Prepare packet
                int packet[fetch_size];
                for (int j = 0; j < fetch_size; j++) {
                        packet[j] = xs[(i * fetch_size) + j];
                }

                printf("[");
                for (int j = 0; j < fetch_size; j++) {
                        printf("%d,", packet[j]);
                        top->S0_AXIS_TDATA[j] = packet[j];
                }

                increment_eval(contextp, top);

                printf("]\n");
                top->S0_AXIS_TVALID = 1;

                if (top->S0_AXIS_TREADY) {
                        i++;
                }
                iter++;


        }
        // AXI4-Stream spec says if we have nothing else to give
        // then S0_AXIS_TVALID goes down.
        top->S0_AXIS_TVALID = 0;

        while (top->O_VALID && iter < (MAX_ITER * 2)) {
                increment_eval(contextp, top);
                iter++;
        }

        // Second iteration
        i = 0;
        correct_out = PACKET_START;
        while (i < packets && iter < MAX_ITER*3) {
                // Prepare packet
                int packet[fetch_size];
                for (int j = 0; j < fetch_size; j++) {
                        packet[j] = xs[(i * fetch_size) + j];
                }

                printf("[");
                for (int j = 0; j < fetch_size; j++) {
                        printf("%d,", packet[j]);
                        top->S0_AXIS_TDATA[j] = packet[j];
                }
                printf("]\n");
                top->S0_AXIS_TVALID = 1;

                if (top->S0_AXIS_TREADY) {
                        i++;
                }
                iter++;

                increment_eval(contextp, top);
        }
        top->S0_AXIS_TVALID = 0;

        while (top->O_VALID && iter < (MAX_ITER * 4)) {
                increment_eval(contextp, top);
                iter++;
        }

        top->final();
        return 0;
}
