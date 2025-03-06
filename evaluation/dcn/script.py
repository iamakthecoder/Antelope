import os
import subprocess

congestion_algos = ["cubic", "bbr", "westwood", "illinois", "vegas"]

for cc in congestion_algos:
    cmd1 = f"sudo modprobe -a tcp_{cc}"
    cmd2 = f"sudo sysctl net.ipv4.tcp_congestion_control={cc}"
    os.system(cmd1)
    os.system(cmd2)

    result = subprocess.run(["sysctl", "net.ipv4.tcp_congestion_control"], capture_output=True, text=True)
    if cc not in result.stdout:
        print(f"Error: {cc} not set as congestion control algorithm")
        exit(1)

    cmd = f"sudo python3 generateData.py --cc {cc}"
    result = subprocess.run(cmd.split(), capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        exit(1)