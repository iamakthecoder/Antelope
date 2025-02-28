/* Copyright (c) 2017 Facebook
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of version 2 of the GNU General Public
 * License as published by the Free Software Foundation.
 *
 * BPF program to set base_rtt to 80us when host is running TCP-NV and
 * both hosts are in the same datacenter (as determined by IPv6 prefix).
 *
 * Use load_sock_ops to load this BPF program.
 */
#include <linux/bpf.h>
#include <linux/bpf_common.h>
#include <sys/socket.h>
#include <linux/types.h>
#include <netinet/tcp.h>
#include <linux/swab.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(key_size, sizeof(__u32));
    __uint(value_size, 10);
    __uint(max_entries, 1024);
    __uint(pinning, LIBBPF_PIN_BY_NAME);
} cong_map SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(key_size, sizeof(__u32));
    __uint(value_size, 10);
    __uint(max_entries, 1024);
    __uint(pinning, LIBBPF_PIN_BY_NAME);  
} ip_cong_map SEC(".maps");

static __always_inline int ebpf_strcmp(const char *str1, const char *str2, int max_len) {
    char c1, c2;
    #pragma clang loop unroll(full) // Unroll loop for verifier safety
    for (int i = 0; i < max_len; i++) {

        // Safely read one byte from str1
        if (bpf_probe_read_kernel(&c1, sizeof(c1), &str1[i]) != 0) {
            // If memory access fails, terminate comparison
            return -1; // Indicate an error
        }

        // Safely read one byte from str2
        if (bpf_probe_read_kernel(&c2, sizeof(c2), &str2[i]) != 0) {
            // If memory access fails, terminate comparison
            return -1; // Indicate an error
        }

        // Check for null termination in either string
        if (c1 == '\0' && c2 == '\0') {
            return 0; // Strings are equal
        }
        if (c1 == '\0' || c2 == '\0') {
            return c1 - c2; // Strings are not equal (different lengths)
        }

        // Compare characters
        if (c1 != c2) {
            return c1 - c2; // Strings are not equal
        }
    }

    // If we reach here, the strings are equal up to max_len
    return 0;
}

SEC("sockops")
int bpf_basertt(struct bpf_sock_ops *skops)
{
	char ip_cong[20], cong[20];
    int op = (int)skops->op;
	long dport = (long)bpf_ntohl(skops->remote_port);
	long lport = (long)skops->local_port;
	long nlip = (long)bpf_ntohl(skops->local_ip4);
	long ndip = (long)bpf_ntohl(skops->remote_ip4);

	// TODO: remove this, if need be
	if (lport!=10010){
		return 1;
	}
	
    long ip_cc_id = ndip, cc_id = dport;
    int key = 0, ikey = 3354, res;
    char *ip_con_str, *con_str;
    char a[10] = "illinois";
    char b[10] = "dctcp";

    bpf_map_update_elem(&cong_map, &key, a, BPF_ANY);
    bpf_map_update_elem(&ip_cong_map, &ikey, b, BPF_ANY);
	bpf_printk("************************************");
    bpf_printk("dport :%ld lport:%ld\n", dport, lport);
	bpf_printk("nlip :%ld ndip:%ld\n", nlip, ndip);

    switch (op)
	{
	case BPF_SOCK_OPS_TCP_ACK_CB:
		bpf_printk("enter BPF_SOCK_OPS_TCP_ACK_CB\n");

		con_str = bpf_map_lookup_elem(&cong_map, &cc_id);
		if (con_str != NULL){
			bpf_printk("cc in map for dport: %d is %s\n", cc_id, con_str);
		}
		else{
			bpf_printk("cc in map for dport: %d is NULL\n", cc_id);
		}
		bpf_getsockopt(skops, SOL_TCP, TCP_CONGESTION, cong, sizeof(cong));
		bpf_printk("current cc for dport: %d is %s\n", cc_id, cong);

		if (con_str == NULL)
		{
			return 1;
		}

		if(ebpf_strcmp(cong, con_str, 10) == 0){
			bpf_printk("cc for dport:%d is already %s\n", cc_id, con_str);
			return 1;
		}

		bpf_setsockopt(skops, SOL_TCP, TCP_CONGESTION, con_str, 10);
		bpf_getsockopt(skops, SOL_TCP, TCP_CONGESTION, cong, sizeof(cong));
		//int r = bpf_map_delete_elem(&cong_map, &cc_id);
		//if (r == 0)
			//bpf_printk("Element deleted from the map\n");
		//else
		//	bpf_printk("Failed to delete element from the map: %d\n", r);
		//break;

		bpf_printk("after change, cc for dport:%d is %s\n", cc_id, cong);

		break;

	case BPF_SOCK_OPS_ACTIVE_ESTABLISHED_CB:
	case BPF_SOCK_OPS_PASSIVE_ESTABLISHED_CB:
		bpf_printk("enter BPF_SOCK_OPS_ACTIVE_ESTABLISHED_CB or BPF_SOCK_OPS_PASSIVE_ESTABLISHED_CB\n");
		
		ip_con_str = bpf_map_lookup_elem(&ip_cong_map, &ip_cc_id);
		if (ip_con_str != NULL){
			bpf_printk("cc in map for dip: %d is %s\n", ip_cc_id, ip_con_str);
		}
		else{
			bpf_printk("cc in map for dip: %d is NULL\n", ip_cc_id);
		}
		
		bpf_getsockopt(skops, SOL_TCP, TCP_CONGESTION, ip_cong, sizeof(ip_cong));
		bpf_printk("current cc for dip: %d is %s\n", ip_cc_id, ip_cong);

		if (ip_con_str == NULL)
		{
			return 1;
		}

		if(ebpf_strcmp(ip_cong, ip_con_str, 10) == 0){
			bpf_printk("cc for dip:%d is already %s\n", ip_cc_id, ip_con_str);
			return 1;
		}

		bpf_setsockopt(skops, SOL_TCP, TCP_CONGESTION, ip_con_str, 10);
		bpf_getsockopt(skops, SOL_TCP, TCP_CONGESTION, ip_cong, sizeof(ip_cong));

		bpf_printk("after change, cc for dip:%d is %s\n", ip_cc_id, ip_cong);
		break;

	case BPF_SOCK_OPS_TCL_CLOSE_CB:
		bpf_printk("enter BPF_SOCK_OPS_TCL_CLOSE_CB\n");
		res = bpf_map_delete_elem(&cong_map, &dport);
		if (res == 0)
			bpf_printk("Element deleted from the map for dport: %d\n", dport);
		else
			bpf_printk("Failed to delete element from the map (return value: %d) for dport: %d\n", res, dport);
		break;
	default:
		bpf_printk("enter default (for dport: %d)\n", dport);
		break;
	}

    skops->reply = 0; //TODO: check this; skops->reply is being set to 0 in the antelope original code, but to -1 in the Subhrendu repo

	return 1;
}
char _license[] SEC("license") = "GPL";