#include <uapi/linux/ptrace.h>
#include <net/sock.h>
#include <linux/tcp.h>

#define SOCKET_FILTER 1 // 1 to filter out all the sockets except the one with port FILTERED_SOCKET_NUM, 0 to not filter
#define FILTERED_SOCKET_NUM 10010 // port number of the socket to be filtered

// separate data structs for ipv4 and ipv6 (only difference is the saddr and daddr fields data type, rest is same)
// struct to store required flow data (in ipv4 tcp_ack event), to transfer from ebpf to user space
struct ipv4_data_t {
    u32 pid;
    u64 ip;
    u32 saddr;
    u32 daddr;
    u16 lport;
    u16 dport;
    u64 state;
    u64 tcp_state;
    u64 srtt;
    u64 rtt;
    u64 mdev;
    u64 mdev_max;
    u64 rttvar;
    u64 min_rtt;
    u64 inflight;
    u64 lost;
    u64 recv_rtt;
    u64 tsoffset;
    u64 retrans_out;
    u64 total_lost;
    u64 sack_out;
    u64 total_retrans;
    u64 tstamp;
    u64 rcv_buf;
    u64 snd_buf;
    u64 snd_cwnd;
    u64 sk_max_pacing_rate;
    u64 sk_pacing_rate;
    u64 delivered;
};
BPF_PERF_OUTPUT(ipv4_events); // perf output buffer to transfer data from ebpf to user space (in ipv4 tcp_ack event)

// struct to store required flow data (in ipv6 tcp_ack event), to transfer from ebpf to user space
struct ipv6_data_t {
    u32 pid;
    u64 ip;
    unsigned __int128 saddr;
    unsigned __int128 daddr;
    u16 lport;
    u16 dport;
    u64 state;
    u64 tcp_state;
    u64 srtt;
    u64 rtt;
    u64 mdev;
    u64 mdev_max;
    u64 rttvar;
    u64 min_rtt;
    u64 inflight;
    u64 lost;
    u64 recv_rtt;
    u64 tsoffset;
    u64 retrans_out;
    u64 total_lost;
    u64 sack_out;
    u64 total_retrans;
    u64 tstamp;
    u64 rcv_buf;
    u64 snd_buf;
    u64 snd_cwnd;
    u64 sk_max_pacing_rate;
    u64 sk_pacing_rate;
    u64 delivered;
};
BPF_PERF_OUTPUT(ipv6_events); // perf output buffer to transfer data from ebpf to user space (in ipv6 tcp_ack event)

// tracepoint handler for tcp_ack event (it fills in the required flow data and sends it to user space)
int trace_ack(struct pt_regs *ctx, struct sock *sk) {
    if (sk == NULL) {
        return 0;
    }

    if (SOCKET_FILTER){
        if (sk->__sk_common.skc_num != FILTERED_SOCKET_NUM){ // filter out all the sockets except the one with port 10010
            return 0;
        }
    }
    // pull in details
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    u16 family = sk->__sk_common.skc_family;
    u16 lport = sk->__sk_common.skc_num; //in host order
    u16 dport = sk->__sk_common.skc_dport; //needs to be converted in host order
    dport = ntohs(dport);
    char state = sk->__sk_common.skc_state;
    struct tcp_sock *tp = (struct tcp_sock *)sk;
    struct tcp_rack rack = tp->rack;
    struct minmax min = tp->rtt_min;
    struct inet_connection_sock *icsk = inet_csk(sk);
    u64 tcp_state=0;

    if (family == AF_INET){ // ipv4
        struct ipv4_data_t data4 = {};
        // fill in the saddr and daddr fields (32 bits for ipv4)
        bpf_probe_read_kernel(&data4.saddr, sizeof(data4.saddr), &sk->__sk_common.skc_rcv_saddr);
        data4.saddr = ntohl(data4.saddr);
        bpf_probe_read_kernel(&data4.daddr, sizeof(data4.daddr), &sk->__sk_common.skc_daddr);
        data4.daddr = ntohl(data4.daddr);
        // fill in the rest of the (common) fields
        data4.delivered = tp->delivered;
        data4.pid = pid;
        data4.ip = 4;
        data4.sk_pacing_rate = sk->sk_pacing_rate;
        data4.sk_max_pacing_rate = sk-> sk_max_pacing_rate;
        data4.srtt = tp->srtt_us;
        data4.rtt = rack.rtt_us;
        data4.mdev = tp->mdev_us;
        data4.mdev_max = tp->mdev_max_us;
        data4.rttvar = tp->rttvar_us;
        data4.min_rtt = min.s[0].v;
        data4.inflight = tp->packets_out;
        data4.lost = tp->lost_out;
        data4.recv_rtt = tp->rcv_rtt_est.rtt_us;
        data4.tcp_state = tcp_state;
        data4.lport = lport;
        data4.dport = dport;
        data4.tsoffset = tp->tsoffset;
        data4.retrans_out = tp->retrans_out;
        data4.total_lost = tp->lost;
        data4.sack_out = tp->sacked_out;
        data4.total_retrans = tp->total_retrans;
        data4.tstamp = tp->lsndtime;
        data4.snd_cwnd = tp->snd_cwnd;
        data4.rcv_buf = sk->sk_rcvbuf;
        data4.snd_buf = sk->sk_sndbuf;
        data4.state = state;

        ipv4_events.perf_submit(ctx, &data4, sizeof(data4)); // send the data to user space
    }
    else if(family == AF_INET6){ // ipv6
        struct ipv6_data_t data6 = {};
        // fill in the saddr and daddr fields (128 bits for ipv6)
        bpf_probe_read(&data6.saddr, sizeof(data6.saddr),
            sk->__sk_common.skc_v6_rcv_saddr.in6_u.u6_addr32);
        bpf_probe_read(&data6.daddr, sizeof(data6.daddr),
            sk->__sk_common.skc_v6_daddr.in6_u.u6_addr32);
        // TODO: convert the saddr and daddr to host order (works as of now, since it is being saved in network order, and being output in the getSocketInfo.py file as it is, in the same order as well)
        // fill in the rest of the (common) fields
        data6.delivered = tp->delivered;
        data6.pid = pid;
        data6.ip = 6;
        data6.sk_pacing_rate = sk->sk_pacing_rate;
        data6.sk_max_pacing_rate = sk-> sk_max_pacing_rate;
        data6.srtt = tp->srtt_us;
        data6.rtt = rack.rtt_us;
        data6.mdev = tp->mdev_us;
        data6.mdev_max = tp->mdev_max_us;
        data6.rttvar = tp->rttvar_us;
        data6.min_rtt = min.s[0].v;
        data6.inflight = tp->packets_out;
        data6.lost = tp->lost_out;
        data6.recv_rtt = tp->rcv_rtt_est.rtt_us;
        data6.tcp_state = tcp_state;
        data6.lport = lport;
        data6.dport = dport;
        data6.tsoffset = tp->tsoffset;
        data6.retrans_out = tp->retrans_out;
        data6.total_lost = tp->lost;
        data6.sack_out = tp->sacked_out;
        data6.total_retrans = tp->total_retrans;
        data6.tstamp = tp->lsndtime;
        data6.snd_cwnd = tp->snd_cwnd;
        data6.rcv_buf = sk->sk_rcvbuf;
        data6.snd_buf = sk->sk_sndbuf;
        data6.state = state;

        ipv6_events.perf_submit(ctx, &data6, sizeof(data6)); // send the data to user space
    }

    return 0;
}