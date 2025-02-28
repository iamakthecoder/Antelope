import os
import subprocess

cc_algos = ["cubic", "bbr", "westwood", "vegas", "illinois"]

# bandwidths = [5, 100, 500, 1000]
# bandwidths = [10, 50, 200, 400, 600, 800]
bandwidths = [20, 50, 100, 300, 500, 700, 1000]

# rtts = [1, 10, 50, 100]
# rtts = [5, 20, 40, 60, 80]
rtts = [1, 5, 10, 30, 50, 70, 100]
delays = [x/4 for x in rtts]

# bdps = [0.1, 3, 6]
# bdps = [0.5, 1, 2, 4]
bdps = [0.1, 0.5, 1, 3, 6]

# THIS ALLOWS TO SET SEPARATE CCs IN THE MININET HOST'S NETWORK NAMESPACE
for cc in cc_algos[::-1]:
    cmd1 = f"sudo modprobe -a tcp_{cc}"
    cmd2 = f"sudo sysctl net.ipv4.tcp_congestion_control={cc}"
    os.system(cmd1)
    os.system(cmd2)

for cc in cc_algos:
    # SEPARATE CCs WILL BE SET IN THE MININET HOST'S NETWORK NAMESPACE
    # cmd1 = f"sudo modprobe -a tcp_{cc}"
    # cmd2 = f"sudo sysctl net.ipv4.tcp_congestion_control={cc}"
    # os.system(cmd1)
    # os.system(cmd2)

    # result = subprocess.run(["sysctl", "net.ipv4.tcp_congestion_control"], capture_output=True, text=True)
    # if cc not in result.stdout:
    #     print(f"Error: {cc} not set as congestion control algorithm")
    #     exit(1)

    # os.system(f"sudo sysctl -w kernel.cap_last_cap=42") # to allow setting cap_net_admin in mininet (NOT REQUIRED)

    for bw in bandwidths:
        for delay in delays:
            for bdp in bdps:
                for background_cc in cc_algos:
                    for i in range(3):
                        cmd = f"sudo python3 mininet_script.py --cc1 {cc} --cc2 {background_cc} --bw {bw} --delay {delay} --bdp {bdp} --iter {i}"
                        os.system(cmd)


    
