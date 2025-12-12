import os
import re
import json
import numpy as np

class perf:
    def __init__(self, dir, path):
        self.path = path
        self.dir = dir
        self.data = None
        self.timer_start = None
        self.timer_end = None
        self._load_timers()

    def _load_timers(self):
        metadata_dir = os.path.join(self.dir, "data")
        start_file = os.path.join(metadata_dir, "timer_start.txt")
        end_file = os.path.join(metadata_dir, "timer_end.txt")

        if os.path.isfile(start_file):
            with open(start_file, "r") as f:
                self.timer_start = f.read().strip()
        if os.path.isfile(end_file):
            with open(end_file, "r") as f:
                self.timer_end = f.read().strip()

    def _parse_file(self, path):
        data = {}
        line_pattern = re.compile(r"^\s*([\d.,]+)\s+([\d.,]+)\s+\w+\s+(\S+)")
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                match = line_pattern.match(line)
                if match:
                    _, value_str, event = match.groups()
                    value = float(value_str.replace(",", "."))
                    data.setdefault(event, []).append(value)
        return data

    def _calculate_stats(self, data, delta_t):
        result = {}
        for event, values in data.items():
            arr = np.array(values)
            mean = np.mean(arr)
            event_data = {
                "unit": "W",
                "samples": len(arr),
                "min": round(float(np.min(arr)), 2),
                "max": round(float(np.max(arr)), 2),
                "mean": round(float(mean), 2),
                "std": round(float(np.std(arr)), 2),
                "percentiles": {
                    "p25": round(float(np.percentile(arr, 25)), 2),
                    "p50": round(float(np.percentile(arr, 50)), 2),
                    "p75": round(float(np.percentile(arr, 75)), 2),
                    "p90": round(float(np.percentile(arr, 90)), 2),
                    "p95": round(float(np.percentile(arr, 95)), 2),
                    "p99": round(float(np.percentile(arr, 99)), 2),
                },
            }
            if delta_t is not None:
                event_data["consumption"] = round(float(mean * delta_t), 2)
            result[event] = event_data
        return result

    def process(self) -> str:
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"Archivo no encontrado: {self.path}")

        delta_t = None
        if self.timer_start and self.timer_end:
            try:
                delta_t = (int(self.timer_end) - int(self.timer_start)) / 1_000_000
                delta_t = round(delta_t, 2)
            except ValueError:
                delta_t = None

        data = self._parse_file(self.path)
        stats = self._calculate_stats(data, delta_t)

        result = {
            "timer_start": self.timer_start,
            "timer_end": self.timer_end,
            "delta_t_seconds": delta_t,
            "events": stats
        }

        dir_name = os.path.dirname(self.path)
        base_name = os.path.splitext(os.path.basename(self.path))[0]
        output_path = os.path.join(dir_name, f"{base_name}.json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        self.data = result
        return output_path
