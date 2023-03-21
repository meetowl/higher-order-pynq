# Very specific to my setup
VITIS_HLS = /tools/Xilinx/Vitis_HLS/2022.2/bin/vitis_hls
VITIS_EXPORT_DIR = /home/meetowl/Documents/add_reduce/exports/add_reduce

VIVADO = /tools/Xilinx/Vivado/2022.2/bin/vivado
VIVADO_PROJ_DIR = /home/meetowl/Documents/pynq-stream
#PYNQ_DIR = /home/meetowl/pynq/jupyter_notebooks/experimentation
PYNQ_DIR = /home/meetowl/pynq/hop/overlays/add_reduce


# Produces $(VITIS_EXPORT_DIR)/export.zip
csynth: add_reduce.cpp
	$(VITIS_HLS) -f ./synth_export.tcl
	unzip -d $(VITIS_EXPORT_DIR) -o -q $(VITIS_EXPORT_DIR)/export.zip

bitstream: $(VITIS_EXPORT_DIR)/export.zip
	$(VIVADO) -mode batch -source gen_bitstream.tcl
	/home/meetowl/Documents/copy_bit_hwh.sh $(VIVADO_PROJ_DIR) $(PYNQ_DIR)
