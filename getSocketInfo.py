# BCC file to probe in the struct socket parameter information
from bcc import BPF
from socket import inet_ntop, AF_INET, AF_INET6
import ctypes as ct
import struct

# data structure corresponding to 'struct ipv4_data_t' in getSocketInfo_ebpf.c
class Data_ipv4(ct.Structure):
    _fields_ = [
        ("pid", ct.c_uint),
        ("ip", ct.c_ulonglong),
        ("saddr", ct.c_uint),
        ("daddr", ct.c_uint),
        ("lport", ct.c_ushort),
        ("dport", ct.c_ushort),
        ("state", ct.c_ulonglong),
        ("tcp_state", ct.c_ulonglong),
        ("srtt", ct.c_ulonglong),
        ("rtt", ct.c_ulonglong),
        ("mdev", ct.c_ulonglong),
        ("mdev_max", ct.c_ulonglong),
        ("rttvar", ct.c_ulonglong),
        ("min_rtt", ct.c_ulonglong),
        ("inflight", ct.c_ulonglong),
        ("lost", ct.c_ulonglong),
        ("recv_rtt", ct.c_ulonglong),
        ("tsoffset", ct.c_ulonglong),
        ("retrans_out", ct.c_ulonglong),
        ("total_lost", ct.c_ulonglong),
        ("sack_out", ct.c_ulonglong),
        ("total_retrans", ct.c_ulonglong),
        ("tstamp", ct.c_ulonglong),
        ("rcv_buf", ct.c_ulonglong),
        ("snd_buf", ct.c_ulonglong),
        ("snd_cwnd", ct.c_ulonglong),
        ("sk_max_pacing_rate", ct.c_ulonglong),
        ("sk_pacing_rate", ct.c_ulonglong),
        ("delivered", ct.c_ulonglong)
    ]

# data structure corresponding to 'struct ipv6_data_t' in getSocketInfo_ebpf.c
class Data_ipv6(ct.Structure):
    _fields_ = [
        ("pid", ct.c_uint),
        ("ip", ct.c_ulonglong),
        ("saddr", (ct.c_ulonglong * 2)),
        ("daddr", (ct.c_ulonglong * 2)),
        ("lport", ct.c_ushort),
        ("dport", ct.c_ushort),
        ("state", ct.c_ulonglong),
        ("tcp_state", ct.c_ulonglong),
        ("srtt", ct.c_ulonglong),
        ("rtt", ct.c_ulonglong),
        ("mdev", ct.c_ulonglong),
        ("mdev_max", ct.c_ulonglong),
        ("rttvar", ct.c_ulonglong),
        ("min_rtt", ct.c_ulonglong),
        ("inflight", ct.c_ulonglong),
        ("lost", ct.c_ulonglong),
        ("recv_rtt", ct.c_ulonglong),
        ("tsoffset", ct.c_ulonglong),
        ("retrans_out", ct.c_ulonglong),
        ("total_lost", ct.c_ulonglong),
        ("sack_out", ct.c_ulonglong),
        ("total_retrans", ct.c_ulonglong),
        ("tstamp", ct.c_ulonglong),
        ("rcv_buf", ct.c_ulonglong),
        ("snd_buf", ct.c_ulonglong),
        ("snd_cwnd", ct.c_ulonglong),
        ("sk_max_pacing_rate", ct.c_ulonglong),
        ("sk_pacing_rate", ct.c_ulonglong),
        ("delivered", ct.c_ulonglong)
    ]


# initialize BPF
b = BPF(src_file="getSocketInfo_ebpf.c")
b.attach_kprobe(event="tcp_ack", fn_name="trace_ack")

# from include/net/tcp_states.h:
tcpstate = {}
tcpstate[1] = 'ESTABLISHED'
tcpstate[2] = 'SYN_SENT'
tcpstate[3] = 'SYN_RECV'
tcpstate[4] = 'FIN_WAIT1'
tcpstate[5] = 'FIN_WAIT2'
tcpstate[6] = 'TIME_WAIT'
tcpstate[7] = 'CLOSE'
tcpstate[8] = 'CLOSE_WAIT'
tcpstate[9] = 'LAST_ACK'
tcpstate[10] = 'LISTEN'
tcpstate[11] = 'CLOSING'
tcpstate[12] = 'NEW_SYN_RECV'

state = {}
state[0] = 'open'
state[1] = 'disorder'
state[2] = 'cwr'
state[3] = 'recovery'
state[4] = 'loss'

# print event data (IPv4)
def print_ipv4_event(cpu, data, size):
    event = ct.cast(data, ct.POINTER(Data_ipv4)).contents # cast data to Data_ipv4
    saddr = inet_ntop(AF_INET, struct.pack("!I", event.saddr)) # convert saddr to human readable format (presentation order)
    daddr = inet_ntop(AF_INET, struct.pack("!I", event.daddr)) # convert daddr to human readable format (presentation order)

    print(event.tstamp,
            saddr,
            event.lport,
            daddr,
            event.dport,
            event.srtt,
            event.mdev,
            event.min_rtt,
            event.inflight,
            event.total_lost,
            event.total_retrans,
            event.rcv_buf,
            event.snd_buf,
            event.snd_cwnd,
            tcpstate[event.state],
            state[event.tcp_state],
            event.sk_pacing_rate,
            event.sk_max_pacing_rate,
            event.delivered
            , flush=True)

# print event data (IPv6)
def print_ipv6_event(cpu, data, size):
    event = ct.cast(data, ct.POINTER(Data_ipv6)).contents
    # TODO: since the saddr and daddr (in case of IPv6) are being saved without converting to host order in the getSocketInfo_ebpf.c file, it is being output here as it is (and hence no need to do explicit conversion to network order)
    saddr = inet_ntop(AF_INET6, struct.pack("QQ", event.saddr[0], event.saddr[1])) # convert saddr to human readable format (presentation order)
    daddr = inet_ntop(AF_INET6, struct.pack("QQ", event.daddr[0], event.daddr[1])) # convert daddr to human readable format (presentation order)

    print(event.tstamp,
            saddr,
            event.lport,
            daddr,
            event.dport,
            event.srtt,
            event.mdev,
            event.min_rtt,
            event.inflight,
            event.total_lost,
            event.total_retrans,
            event.rcv_buf,
            event.snd_buf,
            event.snd_cwnd,
            tcpstate[event.state],
            state[event.tcp_state],
            event.sk_pacing_rate,
            event.sk_max_pacing_rate,
            event.delivered
            , flush=True)

b["ipv4_events"].open_perf_buffer(print_ipv4_event) # open perf buffer to read ipv4 events
b["ipv6_events"].open_perf_buffer(print_ipv6_event) # open perf buffer to read ipv6 events

while True:
    b.perf_buffer_poll() # read events
