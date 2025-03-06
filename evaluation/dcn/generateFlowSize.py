import os
import random

flow_types = ["long", "short", "mixed"]

num_iterations = 30

for flow_type in flow_types:
    filename = f"flowSize_{flow_type}.txt"
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, filename)
    with open(file_path, 'w') as file:
        pass

    min_flow_size = 1024 #1KB
    max_flow_size = 50*1024*1024 #50MB

    if flow_type == "long":
        min_flow_size = 3*1024*1024 #3MB
    elif flow_type == "short":
        max_flow_size = 3*1024*1024 #3MB

    for i in range(num_iterations):
        flow_size = random.randint(min_flow_size, max_flow_size)
        with open(file_path, 'a') as file:
            file.write(f"{flow_size}\n")
