#include <vector>
#include <iostream>
#include "verilated.h"
#include "Vlist_cache.h"

#define LIST_SIZE 100
#define increment_eval() for (int i = 0; i < 2; i++) { lc->timeInc(1); top->CLK = !top->CLK; top->eval(); }

int main(int argc, char** argv, char** env) {
        // Prevent unused variable warnings
        if (false && argc && argv && env) {}

        const std::unique_ptr<VerilatedContext> lc{new VerilatedContext};
        Verilated::traceEverOn(true);
        lc->debug(0);
        lc->randReset(2);
        lc->traceEverOn(true);
        lc->commandArgs(argc, argv);
        const std::unique_ptr<Vlist_cache> top{new Vlist_cache{lc.get(), "TOP"}};

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

        // Process
        for (int i = 0; i < LIST_SIZE; i += 1) {
                // Python Side
                top->LIST_NEXT_READY = 0;
                increment_eval();

                // IP Side
                top->ARG_RECEIVED = 0;
                increment_eval();

                // Python Side
                top->LIST_IN = xs[i];
                top->LIST_NEXT_READY = 1;
                increment_eval();

                // IP Side
                int argin = top->ARG_OUT;
                top->ARG_RECEIVED = 1;
                increment_eval();

        }
        top->final();
        return 0;
}
