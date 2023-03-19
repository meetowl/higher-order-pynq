#include "ap_axi_sdata.h"
#include "hls_stream.h"


void list_cache(hls::stream<ap_axis<32>> &IN,
                uint32_t OUT) {
#pragma HLS INTERFACE axis port=IN
#pragma HLS INTERFACE ap_stable port=OUT
#pragma HLS INTERFACE s_axilite port=return

	ap_axis<32,2,5,6> tmp;
        while(1) {
                A.read(tmp);
                tmp.data = tmp.data.to_int() + 5;
                B.write(tmp);
                if(tmp.last) {
                        break;
                }
        }


}
