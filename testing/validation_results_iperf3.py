import json
import matplotlib.pyplot as plt

time_gap = 10

def parse_iperf_log(file_path):
    with open(file_path, "r") as file:
        json_text = file.readlines()

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

    bitrates_kbps = []
    times = []

    for obj in json_objects:
        try:
            data = json.loads(obj)
            if "intervals" in data:
                for interval in data["intervals"]:
                    sum_data = interval.get("sum", {})
                    if "bits_per_second" in sum_data and "end" in sum_data:
                        bitrates_kbps.append(int(sum_data["bits_per_second"])/1024)  # Convert to kbps
                        times.append(int(sum_data["end"]))  # Convert to int
        except json.JSONDecodeError:
            continue

    return times, bitrates_kbps

class antelope:
    def __init__(self, file_path):
        self.file_path = file_path
        self.time_intervals, self.bitrates = parse_iperf_log(self.file_path)

class bbr:
    def __init__(self, file_path):
        self.file_path = file_path
        self.time_intervals, self.bitrates = parse_iperf_log(self.file_path)

def plot_bitrate(antelope_server, antelope_client, bbr_server, bbr_client):
    plt.plot(antelope_server.time_intervals, antelope_server.bitrates, label='Antelope Server', linestyle='-', color='lightblue')
    plt.plot(antelope_client.time_intervals, antelope_client.bitrates, label='Antelope Client', linestyle='-', color='darkblue')
    plt.plot(bbr_server.time_intervals, bbr_server.bitrates, label='BBR Server', linestyle='-', color='lightgreen')
    plt.plot(bbr_client.time_intervals, bbr_client.bitrates, label='BBR Client', linestyle='-', color='darkgreen')

    plt.axvline(x=time_gap, color='red', linestyle='--', label='Background Traffic Start')
    plt.legend()

    plt.xlabel('Time (seconds)')
    plt.ylabel('Bitrate (Kbits/sec)')
    plt.title('iPerf3 Bitrate vs Time')
    plt.grid(True)
    plt.savefig('bitrate_comparison.png')

if __name__ == "__main__":
    antelope_server_file = "h1_server_antelope.log"  # Change this to your actual file path
    bbr_server_file = "h1_server_bbr.log"  # Change this to your actual file path
    antelope_client_file = "h2_client_antelope.log"  # Change this to your actual file path
    bbr_client_file = "h2_client_bbr.log"  # Change this to your actual file path
    antelope_server = antelope(antelope_server_file)
    bbr_server = bbr(bbr_server_file)
    antelope_client = antelope(antelope_client_file)
    bbr_client = bbr(bbr_client_file)
    plot_bitrate(antelope_server, antelope_client, bbr_server, bbr_client)
