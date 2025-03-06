import json
import os
import matplotlib.pyplot as plt
import numpy as np

congestion_algos = ["antelope", "cubic", "bbr", "westwood", "illinois", "vegas"]

def get_throughput_and_rtt(cc, flow_type):
    throughput = []
    rtt = []
    for file in os.listdir(os.path.dirname(__file__)):
        if file.startswith(f"{cc}_server_{flow_type}"):
            filepath = os.path.join(os.path.dirname(__file__), file)
            with open(filepath, "r") as f:
                json_text = f.readlines()

            # Extract individual JSON objects
            json_objects = []
            current_json = []
            brace_count = 0

            for line in json_text:
                if "{" in line:
                    brace_count += line.count("{")
                if "}" in line:
                    brace_count -= line.count("}")
                
                current_json.append(line)
                
                if brace_count == 0 and current_json:
                    json_objects.append("".join(current_json))
                    current_json = []
                    break

            for obj in json_objects:
                try:
                    data = json.loads(obj)
                    if "end" in data:
                        throughput.append(data["end"]["sum_received"]["bits_per_second"]/1024/1024/8)  # Convert to MBps (from bps)
                except json.JSONDecodeError:
                    continue

        if file.startswith(f"{cc}_client_{flow_type}"):
            filepath = os.path.join(os.path.dirname(__file__), file)
            with open(filepath, "r") as f:
                json_text = f.readlines()

            # Extract individual JSON objects
            json_objects = []
            current_json = []
            brace_count = 0

            for line in json_text:
                if "{" in line:
                    brace_count += line.count("{")
                if "}" in line:
                    brace_count -= line.count("}")
                
                current_json.append(line)
                
                if brace_count == 0 and current_json:
                    json_objects.append("".join(current_json))
                    current_json = []
                    break

            for obj in json_objects:
                try:
                    data = json.loads(obj)
                    if "intervals" in data:
                        for interval in data["intervals"]:
                            rtt.append((interval["streams"][0]["rtt"])/1000) # Convert to ms (from us)
                except json.JSONDecodeError:
                    continue

    return throughput, rtt


def make_graph(throughput, rtt, flow_type):
    plt.figure(figsize=(10, 6))

    for i, cc in enumerate(congestion_algos):
        # Calculate average throughput
        avg_throughput = np.mean(throughput[cc])
        
        # Calculate RTT statistics
        avg_rtt = np.mean(rtt[cc])
        p95_rtt = np.percentile(rtt[cc], 95)
        
        # Get a unique color for each algorithm
        color = plt.cm.tab10(i % 10)  # Using tab10 colormap with 10 distinct colors
        
        # Plot horizontal line from average RTT to 95th percentile RTT
        plt.plot([avg_rtt, p95_rtt], [avg_throughput, avg_throughput],
                color=color, linestyle='-', linewidth=2, label=cc)
        
        # Plot average RTT marker (circle)
        plt.scatter(avg_rtt, avg_throughput, color=color, s=80, marker='o', zorder=3)
        

    plt.xlabel('RTT (ms)\nHorizontal line shows average to 95th percentile')
    plt.ylabel('Throughput (MBps)\nDots represent average values')
    plt.title('Throughput vs RTT Characteristics by Congestion Control Algorithm')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')  # Legend outside on right
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()

    # Save the plot
    plt.savefig(f'DCN_{flow_type}.png', dpi=300, bbox_inches='tight')
    plt.close()

#long flows
print("Long flows")
throughput = {}
rtt = {}
for cc in congestion_algos:
    throughput[cc], rtt[cc] = get_throughput_and_rtt(cc, "long")
make_graph(throughput, rtt, "long")

#short flows
print("Short flows")
throughput = {}
rtt = {}
for cc in congestion_algos:
    throughput[cc], rtt[cc] = get_throughput_and_rtt(cc, "short")
make_graph(throughput, rtt, "short")


#mixed flows
print("Mixed flows")
throughput = {}
rtt = {}
for cc in congestion_algos:
    throughput[cc], rtt[cc] = get_throughput_and_rtt(cc, "mixed")
make_graph(throughput, rtt, "mixed")
