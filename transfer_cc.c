#include <stdio.h>
#include <string.h>
#include <bpf/libbpf.h>
#include <bpf/bpf.h>


void updateCongHash(int key, int ipkey_29MSB, int ipkey_3LSB, int result, int ipPredic) {
    char cong[5][9] = {"cubic", "bbr", "westwood", "illinois", "vegas"};
    char *pval = cong[result]; // model/stream prediction
    char *ipval = cong[ipPredic]; // ip prediction
    long ipkey = ipkey_29MSB * 1000 + ipkey_3LSB;
    unsigned int cong_map_fd, ip_cong_map_fd;
    
    ip_cong_map_fd = bpf_obj_get("/sys/fs/bpf/ip_cong_map");
    if (ip_cong_map_fd == -1) {
        perror("bpf_obj_get failed for ip_cong_map");
        return;
    }
    
    cong_map_fd = bpf_obj_get("/sys/fs/bpf/cong_map");
    if (cong_map_fd == -1) {
        perror("bpf_obj_get failed for cong_map");
        return;
    }

    // Update map elements
    int cong_map_update = bpf_map_update_elem(cong_map_fd, &key, pval, BPF_ANY);
    if (cong_map_update<0) {
        perror("bpf_map_update_elem failed for cong_map");
        return;
    }
    int ip_cong_map_update = bpf_map_update_elem(ip_cong_map_fd, &ipkey, ipval, BPF_ANY);
    if (ip_cong_map_update<0) {
        perror("bpf_map_update_elem failed for ip_cong_map");
        return;
    }
}
