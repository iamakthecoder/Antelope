import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import make_interp_spline

class antelope_results:
    def __init__(self, filename):
        self.filename = filename    
        self.throughput = []
        self.cwnd = []
        self.pacing_rate = []
        self.rtt = []
        self.cc = []
        self.background_traffic_point = None

    def calc_results(self):
        with open(self.filename, 'r') as f:
            for line in f:
                line = line.strip()
                line = line.split()
                line = "".join(line)
                line = line.split(':')

                if line[0] == "THROUGHPUT":
                    self.throughput.append((line[1], line[2]))
                
                if line[0] == "CWND":
                    self.cwnd.append((line[1], line[2]))

                if line[0] == "PACINGRATE":
                    self.pacing_rate.append((line[1], line[2]))

                if line[0] == "RTT":
                    self.rtt.append((line[1], line[2]))

                if line[0] == "CC":
                    self.cc.append((line[1], line[2]))

                if "BACKGROUND" in line[0]:
                    self.background_traffic_point = max(self.throughput[-1][0], self.cwnd[-1][0], self.pacing_rate[-1][0], self.rtt[-1][0])


class bbr_results:
    def __init__(self, filename):
        self.filename = filename    
        self.throughput = []
        self.cwnd = []
        self.pacing_rate = []
        self.rtt = []
        self.background_traffic_point = None

    def calc_results(self):
        with open(self.filename, 'r') as f:
            for line in f:
                line = line.strip()
                line = line.split()
                line = "".join(line)
                line = line.split(':')

                if line[0] == "THROUGHPUT":
                    self.throughput.append((line[1], line[2]))
                
                if line[0] == "CWND":
                    self.cwnd.append((line[1], line[2]))

                if line[0] == "PACINGRATE":
                    self.pacing_rate.append((line[1], line[2]))

                if line[0] == "RTT":
                    self.rtt.append((line[1], line[2]))

                if "BACKGROUND" in line[0]:
                    self.background_traffic_point = max(self.throughput[-1][0], self.cwnd[-1][0], self.pacing_rate[-1][0], self.rtt[-1][0])


def compare_throughput(antelope, bbr):
    plt.clf()
    antelope_x = [float(x) for x, y in antelope.throughput]
    antelope_y = [float(y) for x, y in antelope.throughput]
    bbr_x = [float(x) for x, y in bbr.throughput]
    bbr_y = [float(y) for x, y in bbr.throughput]

    plt.plot(antelope_x, antelope_y, label='Antelope Throughput', color='blue', linestyle='-')
    plt.plot(bbr_x, bbr_y, label='BBR Throughput', color='red', linestyle='-')

    for x, _ in antelope.cc:
        plt.axvline(x=float(x), color='green', linestyle=':', linewidth=1)

    plt.axvline(x=float(antelope.background_traffic_point), color='blue', linestyle='--', linewidth=1)
    plt.axvline(x=float(bbr.background_traffic_point), color='red', linestyle='--', linewidth=1)

    plt.xlabel('X Axis')
    plt.ylabel('Throughput')
    plt.title('Throughput Comparison')
    plt.legend()
    plt.savefig('throughput_comparison.png')


def compare_cwnd(antelope, bbr):
    plt.clf()
    antelope_x = [float(x) for x, y in antelope.cwnd]
    antelope_y = [float(y) for x, y in antelope.cwnd]
    bbr_x = [float(x) for x, y in bbr.cwnd]
    bbr_y = [float(y) for x, y in bbr.cwnd]


    plt.plot(antelope_x, antelope_y, label='Antelope CWND', color='blue', linestyle='-')
    plt.plot(bbr_x, bbr_y, label='BBR CWND', color='red', linestyle='-')

    for x, _ in antelope.cc:
        plt.axvline(x=float(x), color='green', linestyle=':', linewidth=1)

    plt.axvline(x=float(antelope.background_traffic_point), color='blue', linestyle='--', linewidth=1)
    plt.axvline(x=float(bbr.background_traffic_point), color='red', linestyle='--', linewidth=1)

    plt.xlabel('X Axis')
    plt.ylabel('CWND')
    plt.title('CWND Comparison')
    plt.legend()
    plt.savefig('cwnd_comparison.png')

def compare_pacing_rate(antelope, bbr):
    plt.clf()
    antelope_x = [float(x) for x, y in antelope.pacing_rate]
    antelope_y = [float(y) for x, y in antelope.pacing_rate]
    bbr_x = [float(x) for x, y in bbr.pacing_rate]
    bbr_y = [float(y) for x, y in bbr.pacing_rate]


    plt.plot(antelope_x, antelope_y, label='Antelope Pacing Rate', color='blue', linestyle='-')
    plt.plot(bbr_x, bbr_y, label='BBR Pacing Rate', color='red', linestyle='-')

    for x, _ in antelope.cc:
        plt.axvline(x=float(x), color='green', linestyle=':', linewidth=1)

    plt.xlabel('X Axis')
    plt.ylabel('Pacing Rate')
    plt.title('Pacing Rate Comparison')
    plt.legend()
    plt.savefig('pacing_rate_comparison.png')

def compare_rtt(antelope, bbr):
    plt.clf()
    antelope_x = [float(x) for x, y in antelope.rtt]
    antelope_y = [float(y) for x, y in antelope.rtt]
    bbr_x = [float(x) for x, y in bbr.rtt]
    bbr_y = [float(y) for x, y in bbr.rtt]


    plt.plot(antelope_x, antelope_y, label='Antelope RTT', color='blue', linestyle='-')
    plt.plot(bbr_x, bbr_y, label='BBR RTT', color='red', linestyle='-')

    for x, _ in antelope.cc:
        plt.axvline(x=float(x), color='green', linestyle=':', linewidth=1)

    plt.axvline(x=float(antelope.background_traffic_point), color='blue', linestyle='--', linewidth=1)
    plt.axvline(x=float(bbr.background_traffic_point), color='red', linestyle='--', linewidth=1)

    plt.xlabel('X Axis')
    plt.ylabel('RTT')
    plt.title('RTT Comparison')
    plt.legend()
    plt.savefig('rtt_comparison.png')

antelope = antelope_results('validation_logs_antelope')
antelope.calc_results()

bbr = bbr_results('validation_logs_bbr')
bbr.calc_results()

compare_throughput(antelope, bbr)
compare_cwnd(antelope, bbr)
compare_pacing_rate(antelope, bbr)
compare_rtt(antelope, bbr)