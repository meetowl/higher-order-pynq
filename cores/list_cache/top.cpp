#include <vector>
#include <iostream>
#include "verilated.h"
#include "Vlist_cache.h"

#define LIST_SIZE 100
#define increment_eval()                                \
        for (int i = 0; i < 2; i++) {                   \
                contextp->timeInc(1);                   \
                top->CLK = !top->CLK;                   \
                top->eval();                            \
        }

int main(int argc, char** argv, char** env) {
        // Prevent unused variable warnings
        if (false && argc && argv && env) {}

        const std::unique_ptr<VerilatedContext> contextp{new VerilatedContext};
        Verilated::traceEverOn(true);
        contextp->debug(0);
        contextp->randReset(2);
        contextp->traceEverOn(true);
        contextp->commandArgs(argc, argv);
        const std::unique_ptr<Vlist_cache> top{new Vlist_cache{contextp.get(), "TOP"}};

        // Initialise the input list
        std::vector<int> xs = std::vector<int>(100);
        for (int i = 0; i < LIST_SIZE; i++) xs[i] = i + 1;

        top->CLK = 0;
        top->RESET = 1;
        // Warm up
        for (int i = 0; i < 10; i++) {
                increment_eval();
        }
        top->RESET = 0;

        // Pin IP ready pin to ready
        top->i_ready = 1;

        // Process
        for (int i = 0; i < LIST_SIZE; i += 1) {
                // Python Side
                top->i_valid = 0;
                increment_eval();

                // Python Side
                top->i_data = xs[i];
                top->i_valid = 1;
                increment_eval();
        }
        top->final();
        return 0;
}
