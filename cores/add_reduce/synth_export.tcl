# I just copied everything vivado did into here

# Open
cd /home/meetowl/Documents
open_project add_reduce
open_solution add_reduce/solution1

# Synthesise
csynth_design

# Exporting
config_export -description {HoP Add-Reduce Module}
config_export -display_name {HoP Add-Reduce}
config_export -format=ip_catalog
config_export -library=HoP
config_export -output=/home/meetowl/Documents/add_reduce/exports/add_reduce
config_export -rtl=verilog
config_export -vendor=HoP
config_export -version=0.1
export_design -rtl verilog -format ip_catalog -output /home/meetowl/Documents/add_reduce/exports/add_reduce

exit
