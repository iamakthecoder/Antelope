import os

congestion_algos = ["cubic", "bbr", "westwood", "vegas", "illinois"]

for cc in congestion_algos:
    ebpfdata_folder = "ebpfdata3"

    cnt = 0
    for filename in os.listdir(ebpfdata_folder):
        if filename.startswith(cc):
            filepath = os.path.join(ebpfdata_folder, filename)
            # print(f"Processing {filepath}")
            # Process the file as needed
            cmd = f"sudo python3 generateTrainData.py --cc {cc} --file {filepath}"
            os.system(cmd)

            cnt+=1
    print(f"Processed {cnt} files for {cc}")