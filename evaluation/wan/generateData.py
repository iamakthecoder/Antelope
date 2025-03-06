from mininet.net import Mininet
from mininet.node import Controller
from mininet.link import TCLink
from mininet.topo import Topo
import argparse
import os
import time
import random   

parser = argparse.ArgumentParser(description='Evaluate WAN emulation')
parser.add_argument('--cc', type=str, required=True, help='CC algorithm')

cc = "antelope" #"antelope" or "bbr" or "cubic" and so on

args = parser.parse_args()
cc = args.cc

num_iterations = 30

def emulate_network(bw, delay, bdp, loss, iter, flow_type):
    net = Mininet(link=TCLink)

    c0 = net.addController('c0')

    h1 = net.addHost('h1')
    h2 = net.addHost('h2')

    queue_size = int((((bw*1024*1024) * ((delay * 2)/1000) * bdp)/8)/1500) #in packets

    net.addLink(h1, h2, bw=bw, delay=f"{delay}ms", loss=loss, max_queue_size=queue_size)

    net.start()

    #TODO: TO BE REMOVED, IF USING Antelope
    h1.cmd(f'sysctl -w net.ipv4.tcp_congestion_control={cc}')
    h2.cmd(f'sysctl -w net.ipv4.tcp_congestion_control={cc}')
    curr_cc_h1 = h1.cmd('sysctl -n net.ipv4.tcp_congestion_control').strip()
    curr_cc_h2 = h2.cmd('sysctl -n net.ipv4.tcp_congestion_control').strip()
    if curr_cc_h1 != cc:
        net.stop()
        raise RuntimeError(f"Failed to set CC on h1! Expected {cc}, got {curr_cc_h1}")
    if curr_cc_h2 != cc:
        net.stop()
        raise RuntimeError(f"Failed to set CC on h2! Expected {cc}, got {curr_cc_h2}")
    

    h1_server_logfile = f"{cc}_server_{flow_type}_{iter}.log"
    h2_client_logfile = f"{cc}_client_{flow_type}_{iter}.log"

    flow_size_file = os.path.join(os.path.dirname(__file__), f"flowSize_{flow_type}.txt")
    with open(flow_size_file, 'r') as file:
        flow_sizes = file.readlines()
        flow_size = int(flow_sizes[iter].strip())
    print(f"\tFlow size: {flow_size}")

    for logfile in [h1_server_logfile, h2_client_logfile]:
        if os.path.exists(logfile):
            os.remove(logfile)

    h1.cmd(f"iperf3 -s -p 10020 -i 1 --logfile {h1_server_logfile} --version4 -J &")
    time.sleep(2)

    h2.cmd(f"iperf3 -c {h1.IP()} -p 10020 --cport 10010 --bytes {flow_size} -i 1 --logfile {h2_client_logfile} --version4 -J")

    print("\tDone with the iteration")
    print()

    net.stop()  

#WAN emulation parameters
bandwidth = 11.2 #Mbps (11.2Mbps = 1.4MBps)
delay = 100 #ms
bdp = 5
loss = 1.5 #%

#long flows
print("Running long flows")
for i in range(num_iterations):
    print(f"\tRunning iteration {i}")
    emulate_network(bandwidth, delay, bdp, loss, i, "long")

#short flows
print("Running short flows")
for i in range(num_iterations):
    print(f"\tRunning iteration {i}")
    emulate_network(bandwidth, delay, bdp, loss, i, "short")

#mixed flows
print("Running mixed flows")
for i in range(num_iterations):
    print(f"\tRunning iteration {i}")
    emulate_network(bandwidth, delay, bdp, loss, i, "mixed")