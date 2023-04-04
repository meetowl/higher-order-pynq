# Very specific to my setup
# Opening
open_project /home/meetowl/Documents/pynq-stream/pynq-stream.xpr
update_compile_order -fileset sources_1
open_bd_design {/home/meetowl/Documents/pynq-stream/pynq-stream.srcs/sources_1/bd/pynq_stream/pynq_stream.bd}

# Updating
update_ip_catalog -rebuild -scan_changes
report_ip_status -name ip_status
upgrade_ip -vlnv HoP:HoP:HoP_add_reduce:0.1 [get_ips  pynq_stream_HoP_add_reduce_0_0] -log ip_upgrade.log
export_ip_user_files -of_objects [get_ips pynq_stream_HoP_add_reduce_0_0] -no_script -sync -force -quiet

# Generate Bitstream
reset_run synth_1
launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run synth_1
wait_on_run impl_1

exit
