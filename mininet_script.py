from mininet.net import Mininet
from mininet.node import Controller
from mininet.link import TCLink
from mininet.topo import Topo
import argparse
import os
import time

def emulate_network(bw, delay, bdp, iter, cc1, cc2):

    filename = f"ebpfdata3/{cc1}_{cc2}_{bw}_{delay}_{bdp}_{iter}.txt"
    if os.path.exists(filename):
        return

    net = Mininet(link=TCLink)
    c0 = net.addController('c0')

    # Add hosts
    h1 = net.addHost('h1')
    h2 = net.addHost('h2')
    h3 = net.addHost('h3')
    h4 = net.addHost('h4')

    # Add switches
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')

    queue_size = int(bdp * bw * delay * 8)

    # Add links
    net.addLink(h1, s1, bw=bw, delay=delay, max_queue_size=queue_size)
    net.addLink(h2, s2, bw=bw, delay=delay, max_queue_size=queue_size)
    net.addLink(h3, s1, bw=bw, delay=delay, max_queue_size=queue_size)
    net.addLink(h4, s2, bw=bw, delay=delay, max_queue_size=queue_size)
    net.addLink(s1, s2, bw=bw, delay=delay, max_queue_size=queue_size)

    # Start network
    net.start()

    # Set congestion control algorithms
    # h1.cmd(f"sudo sysctl -w kernel.cap_last_cap=42") #NOT REQUIRED
    # h2.cmd(f"sudo sysctl -w kernel.cap_last_cap=42") #NOT REQUIRED
    h1.cmd(f'sysctl -w net.ipv4.tcp_congestion_control={cc1}')
    h4.cmd(f'sysctl -w net.ipv4.tcp_congestion_control={cc2}')

    # Verify CC configuration
    current_cc_h1 = h1.cmd('sysctl -n net.ipv4.tcp_congestion_control').strip()
    current_cc_h4 = h4.cmd('sysctl -n net.ipv4.tcp_congestion_control').strip()

    if current_cc_h1 != cc1:
        net.stop()
        raise RuntimeError(f"Failed to set CC on h1! Expected {cc1}, got {current_cc_h1}")

    if current_cc_h4 != cc2:
        net.stop()
        raise RuntimeError(f"Failed to set CC on h4! Expected {cc2}, got {current_cc_h4}")

    h1.cmd(f"sudo python3 getSocketInfo.py > {filename} &")

    # Start servers
    h1.cmd(f'python3 -m http.server 10010 &')
    h4.cmd(f'python3 -m http.server 10011 &')

    time.sleep(3)

    h2_download_file = "temp_h2"
    h3_download_file = "temp_h3"
    h2_done_file = "h2_done"
    h3_done_file = "h3_done"

    # Cleanup previous done files
    for f in [h2_download_file, h3_download_file, h2_done_file, h3_done_file]:
        if os.path.exists(f):
            os.remove(f)

    # Start downloads
    h2.cmd(f'wget http://{h1.IP()}:10010/temp -O {h2_download_file} && touch {h2_done_file} &')
    h3.cmd(f'wget http://{h4.IP()}:10011/temp -O {h3_download_file} && touch {h3_done_file} &')

    TIME_LIMIT = 5*60
    time_counter = 0

    # Wait for downloads to complete
    while True:
        if os.path.exists(h2_done_file) and os.path.exists(h3_done_file):
            break
        time.sleep(2)
        time_counter += 2
        if time_counter >= TIME_LIMIT:
            break

    net.stop()

    # Cleanup
    for f in [h2_download_file, h3_download_file, h2_done_file, h3_done_file]:
        if os.path.exists(f):
            os.remove(f)
    # Delete any file starting with the name "wget-log"
    for file in os.listdir('.'):
        if file.startswith("wget-log"):
            os.remove(file)


parser = argparse.ArgumentParser(description='Network Emulation Script')
parser.add_argument('--bw', type=int, required=True, help='Bandwidth (Mbps)')
parser.add_argument('--delay', type=float, required=True, help='Delay (ms)')
parser.add_argument('--bdp', type=float, required=True, help='Bandwidth-Delay Product')
parser.add_argument('--iter', type=int, required=True, help='Iteration number')
parser.add_argument('--cc1', type=str, required=True, help='CC algorithm for h1')
parser.add_argument('--cc2', type=str, required=True, help='CC algorithm for h4')

args = parser.parse_args()

emulate_network(
    bw=args.bw,
    delay=args.delay,
    bdp=args.bdp,
    iter=args.iter,
    cc1=args.cc1,
    cc2=args.cc2
)