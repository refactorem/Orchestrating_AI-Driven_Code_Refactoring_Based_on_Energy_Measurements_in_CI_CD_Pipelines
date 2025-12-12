import os
import shutil
from services.carbon_service import enrich_json_with_carbon_data, fetch_carbon_intensity
from .perf import perf
from .pcm import pcm

class MethodRunner:
    METHODS = {
        "perf": perf,
        "pcm": pcm
    }

    def __init__(self, approach, method, base_dir, path):
        self.approach = approach
        self.method = method
        self.base_dir = base_dir
        self.path = path

    def run(self):
        if self.method not in self.METHODS:
            raise ValueError(f"Unsupported method: {self.method}")
        
        processor_class = self.METHODS[self.method]
        processor = processor_class(self.base_dir, self.path)
        decompressed_json_path = processor.process()

        carbon_data = fetch_carbon_intensity()
        carbon_intensity = carbon_data.get("carbonIntensity")
        if carbon_intensity:
            enrich_json_with_carbon_data(decompressed_json_path, carbon_intensity)

        existing = [d for d in os.listdir(self.base_dir) if d.startswith("measurement")]
        nums = [int(d.replace("measurement", "")) for d in existing if d.replace("measurement", "").isdigit()]
        next_num = max(nums, default=-1) + 1

        target_dir = os.path.join(self.base_dir, f"measurement{next_num}")
        os.makedirs(target_dir)

        items_to_move = ["chunks", "data", "decompressed", "reconstructed.gz", os.path.basename(decompressed_json_path)]
        for item in items_to_move:
            src = os.path.join(self.base_dir, item)
            if os.path.exists(src):
                shutil.move(src, target_dir)

        return os.path.join(target_dir, os.path.basename(decompressed_json_path))
