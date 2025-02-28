from mininet.net import Mininet
from mininet.node import Controller
from mininet.link import TCLink
from mininet.topo import Topo
import argparse
import os
import time

cc_used = "antelope" #"antelope" or "bbr" or else
LOGGING_FILE = f"validation_logs_{cc_used}"

def emulate_network(bw, delay, queue_size):

    net = Mininet(link=TCLink)

    c0 = net.addController('c0')

    h1 = net.addHost('h1')
    h2 = net.addHost('h2')
    h3 = net.addHost('h3')
    h4 = net.addHost('h4')


    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')

    net.addLink(h1, s1, bw=bw, delay=f"{delay}ms")
    net.addLink(h2, s2, bw=bw, delay=f"{delay}ms")
    net.addLink(h3, s1, bw=bw, delay=f"{delay}ms")
    net.addLink(h4, s2, bw=bw, delay=f"{delay}ms")

    net.addLink(s1, s2, bw=bw, delay=f"{delay}ms")

    net.start()

    '''
    USING HTTP SERVER AND WGET
    '''

    # h1.cmd(f"python3 -m http.server 10010 &")
    # time.sleep(2)
    # h2.cmd(f"wget http://{h1.IP()}:10010/temp &")

    # time.sleep(5)

    # h3.cmd(f"python3 -m http.server 10011 &")
    # time.sleep(2)
    # if LOGGING_FILE is not None:
    #     with open(LOGGING_FILE, "a") as f:
    #         f.write("BACKGROUND TRAFFIC START\n")
    #         f.flush()
    #         os.fsync(f.fileno())
    # h4.cmd(f"wget http://{h3.IP()}:10011/temp")

    # time.sleep(5)

    # os.remove("temp.1")
    # os.remove("temp.2")

    '''
    USING IPERF3
    '''

    h1_logfile = f"h1_server_{cc_used}.log"
    h2_logfile = f"h2_client_{cc_used}.log"
    h3_logfile = f"h3_server_{cc_used}.log"
    h4_logfile = f"h4_client_{cc_used}.log"
    time_in_sec = 60
    gap_time = 10

    # Clean up log files if they exist
    for logfile in [h1_logfile, h2_logfile, h3_logfile, h4_logfile]:
        if os.path.exists(logfile):
            os.remove(logfile)

    h1.cmd(f"iperf3 -s -p 10010 -i 1 --logfile {h1_logfile} --version4 -J &")
    h3.cmd(f"iperf3 -s -p 10011 -i 1 --logfile {h3_logfile} --version4 -J &")
    time.sleep(2)
    h2.cmd(f"iperf3 -R -c {h1.IP()} -p 10010 -t {time_in_sec} -i 1 --logfile {h2_logfile} --version4 -J &")
    time.sleep(gap_time)
    if LOGGING_FILE is not None:
        with open(LOGGING_FILE, "a") as f:
            f.write("BACKGROUND TRAFFIC START\n")
            f.flush()
            os.fsync(f.fileno())
    h4.cmd(f"iperf3 -c {h3.IP()} -p 10011 -t {time_in_sec + 1 - gap_time} -i 1 --logfile {h4_logfile} --version4 -J")
    time.sleep(2)

    net.stop()

emulate_network(15, 2, 100)