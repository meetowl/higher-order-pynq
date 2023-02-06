#include <vector>
#include <iostream>
#include "verilated.h"
#include "Vlist_cache.h"

#define LIST_SIZE 100

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
        for (int i = 0; i < LIST_SIZE; i++) xs[i] = i;

        top->CLK = 0;
        top->RESET = 1;

        // Warm up
        for (int i = 0; i < 10; i++) {
                top->CLK = !top->CLK;
                lc->timeInc(1);
                top->eval();
        }
        top->RESET = 0;

        // Process
        for (int i = 0; i < LIST_SIZE; i += 2) {
                lc->timeInc(1);
                top->CLK = !top->CLK;
                // if (top->NEXT) {
                //         top->LIST_IN[0] = xs[i];
                //         top->LIST_IN[1] = xs[i+1];
                // }
                top->eval();
        }
        top->final();
        // delete &top;
        // delete &lc;
        return 0;
}
