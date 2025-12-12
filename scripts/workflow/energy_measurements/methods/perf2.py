import os
import re
import json
import numpy as np

class perf:
    def __init__(self, session_dir: str, original_name: str, timer_start, timer_end, is_baseline):
        self.session_dir = session_dir
        self.original_name = original_name
        self.timer_start = timer_start
        self.timer_end = timer_end
        self.is_baseline = is_baseline
        self.data = None

    def format_time_interval(self, start, end):
        try:
            delta = (int(end) - int(start)) / 1_000_000
            return f"{delta:.3f} s"
        except Exception:
            return "N/A"

    def generate_markdown_table(self, stats):
        headers = [
            "Event", "Samples", "Min", "Max", "Mean", "Std Dev",
            "p25", "p50", "p75", "p90", "p95", "p99", "Consumption (J)"
        ]
        lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]

        for event, data in stats.items():
            percentiles = data.get("percentiles", {})
            line = [
                event,
                str(data.get("samples", "N/A")),
                f"{data.get('min', 0):.3f}" if "min" in data else "N/A",
                f"{data.get('max', 0):.3f}" if "max" in data else "N/A",
                f"{data.get('mean', 0):.3f}" if "mean" in data else "N/A",
                f"{data.get('std', 0):.3f}" if "std" in data else "N/A",
                f"{percentiles.get('p25', 0):.3f}" if "p25" in percentiles else "N/A",
                f"{percentiles.get('p50', 0):.3f}" if "p50" in percentiles else "N/A",
                f"{percentiles.get('p75', 0):.3f}" if "p75" in percentiles else "N/A",
                f"{percentiles.get('p90', 0):.3f}" if "p90" in percentiles else "N/A",
                f"{percentiles.get('p95', 0):.3f}" if "p95" in percentiles else "N/A",
                f"{percentiles.get('p99', 0):.3f}" if "p99" in percentiles else "N/A",
                f"{data.get('consumption', 0):.3f}" if data.get("consumption") is not None else "N/A",
            ]
            lines.append("| " + " | ".join(line) + " |")

        return "\n".join(lines)

    def generate_summary(self):
        print(self.data)
        if not self.data:
            return "_No data to summarize_"
        return self._generate_summary(self.data)

    def _generate_summary(self, data):
        md = "# EcOps Performance Report\n\n"
        measurement_keys = [k for k in data.keys() if k.startswith("measurement_")]
        measurement_keys.sort(key=lambda x: int(x.split("_")[1]))

        for key in measurement_keys:
            measurement = data[key]
            timer_start = measurement.get("timer_start", "N/A")
            timer_end = measurement.get("timer_end", "N/A")
            interval = self.format_time_interval(timer_start, timer_end)

            md += f"## Measurement {key.split('_')[1]} (Interval: {interval})\n\n"
            if "withBaseline" in measurement:
                md += self.generate_markdown_table(measurement["withBaseline"])
                md += "\n\n"
            else:
                md += "_No data available_\n\n"

        if "aggregate" in data:
            agg = data["aggregate"]
            timer_start = agg.get("timer_start", "N/A")
            timer_end = agg.get("timer_end", "N/A")
            interval = self.format_time_interval(timer_start, timer_end)

            md += f"## Aggregate (Interval: {interval})\n\n"
            if "withBaseline" in agg:
                md += self.generate_markdown_table(agg["withBaseline"])
                md += "\n"
            else:
                md += "_No aggregate data available_\n"

        return md

    def process(self) -> str:
        path = os.path.join(self.session_dir, self.original_name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Archivo no encontrado: {path}")

        data = self._parse_file(path)
        result = self._calculate_stats(data)

        output_path = self._get_output_path()
        existing_data = self._load_existing_data(output_path)

        if self.is_baseline:
            if self.timer_start is not None:
                result["timer_start"] = self.timer_start
            if self.timer_end is not None:
                result["timer_end"] = self.timer_end

            existing_data["baseline"] = result

            self._update_measurements_without_baseline(existing_data)
        else:
            next_index = self._get_next_measurement_index(existing_data)
            key = f"measurement_{next_index}"

            measurement_entry = {}
            if self.timer_start is not None:
                measurement_entry["timer_start"] = self.timer_start
            if self.timer_end is not None:
                measurement_entry["timer_end"] = self.timer_end

            measurement_entry["withBaseline"] = result

            if "baseline" in existing_data:
                baseline_data = existing_data["baseline"]
                measurement_entry["withoutBaseline"] = self._create_without_baseline(baseline_data, result)

            existing_data[key] = measurement_entry

        self._create_aggregate(existing_data)
        self._save_data(output_path, existing_data)
        os.remove(path)

        self.data = existing_data

        return output_path

    def _update_measurements_without_baseline(self, existing_data):
        if "baseline" not in existing_data:
            return

        baseline_data = existing_data["baseline"]
        updated = False

        for key, measurement in existing_data.items():
            if not key.startswith("measurement_"):
                continue
            if "withBaseline" in measurement and "withoutBaseline" not in measurement:
                measurement["withoutBaseline"] = self._create_without_baseline(
                    baseline_data, measurement["withBaseline"]
                )
                updated = True

        if updated:
            output_path = self._get_output_path()
            self._save_data(output_path, existing_data)

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

    def _calculate_stats(self, data):
        result = {}
        delta_t = None
        if self.timer_start and self.timer_end:
            try:
                delta_t = (int(self.timer_end) - int(self.timer_start)) / 1_000_000
            except ValueError:
                delta_t = None

        for event, values in data.items():
            arr = np.array(values)
            mean = np.mean(arr)
            event_data = {
                "unit": "W",
                "samples": len(arr),
                "min": round(float(np.min(arr)), 3),
                "max": round(float(np.max(arr)), 3),
                "mean": round(float(mean), 3),
                "std": round(float(np.std(arr)), 3),
                "percentiles": {
                    "p25": round(float(np.percentile(arr, 25)), 3),
                    "p50": round(float(np.percentile(arr, 50)), 3),
                    "p75": round(float(np.percentile(arr, 75)), 3),
                    "p90": round(float(np.percentile(arr, 90)), 3),
                    "p95": round(float(np.percentile(arr, 95)), 3),
                    "p99": round(float(np.percentile(arr, 99)), 3),
                },
            }
            if delta_t is not None:
                event_data["consumption"] = round(float(mean * delta_t), 3)

            result[event] = event_data
        return result

    def _get_output_path(self):
        base_name, _ = os.path.splitext(self.original_name)
        return os.path.join(self.session_dir, f"{base_name}.json")

    def _load_existing_data(self, output_path):
        if os.path.exists(output_path):
            with open(output_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_data(self, output_path, data):
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _get_next_measurement_index(self, existing_data):
        indices = [
            int(k.split("_")[1]) for k in existing_data.keys()
            if k.startswith("measurement_") and k.split("_")[1].isdigit()
        ]
        return max(indices) + 1 if indices else 0

    def _create_without_baseline(self, baseline_data, measurement_data):
        def calc_stats(values, delta_t=None):
            arr = np.array(values)
            mean = np.mean(arr)
            event_data = {
                "unit": "W",
                "samples": len(arr),
                "min": round(float(np.min(arr)), 3),
                "max": round(float(np.max(arr)), 3),
                "mean": round(float(mean), 3),
                "std": round(float(np.std(arr)), 3),
                "percentiles": {
                    "p25": round(float(np.percentile(arr, 25)), 3),
                    "p50": round(float(np.percentile(arr, 50)), 3),
                    "p75": round(float(np.percentile(arr, 75)), 3),
                    "p90": round(float(np.percentile(arr, 90)), 3),
                    "p95": round(float(np.percentile(arr, 95)), 3),
                    "p99": round(float(np.percentile(arr, 99)), 3),
                },
            }
            if delta_t is not None:
                event_data["consumption"] = round(float(mean * delta_t), 3)
            return event_data

        corrected = {}

        delta_t = None
        timer_start = measurement_data.get("timer_start")
        timer_end = measurement_data.get("timer_end")
        if timer_start and timer_end:
            try:
                delta_t = (int(timer_end) - int(timer_start)) / 1_000_000
            except Exception:
                delta_t = None

        for event in measurement_data:
            if event in ("timer_start", "timer_end"):
                continue
            if event in baseline_data and event in measurement_data:
                baseline_mean = baseline_data[event].get("mean", 0)
                measured_mean = measurement_data[event].get("mean", 0)
                diff = measured_mean - baseline_mean
                if diff < 0:
                    diff = 0
                corrected[event] = {
                    "unit": "W",
                    "samples": measurement_data[event].get("samples", 0),
                    "min": max(0, measurement_data[event].get("min", 0) - baseline_data[event].get("min", 0)),
                    "max": max(0, measurement_data[event].get("max", 0) - baseline_data[event].get("max", 0)),
                    "mean": diff,
                    "std": measurement_data[event].get("std", 0),
                    "percentiles": {
                        p: max(0, measurement_data[event].get("percentiles", {}).get(p, 0) - baseline_data[event].get("percentiles", {}).get(p, 0))
                        for p in ["p25", "p50", "p75", "p90", "p95", "p99"]
                    },
                    "consumption": max(0, measurement_data[event].get("consumption", 0) - baseline_data[event].get("consumption", 0)),
                }
            else:
                corrected[event] = measurement_data[event]

        return corrected

  
    def _create_aggregate(self, existing_data):
        measurements_with_baseline = [
            v.get("withBaseline", {})
            for k, v in existing_data.items()
            if k.startswith("measurement_") and "withBaseline" in v
        ]

        measurements_without_baseline = [
            v.get("withoutBaseline", {})
            for k, v in existing_data.items()
            if k.startswith("measurement_") and "withoutBaseline" in v
        ]

        if not measurements_with_baseline:
            return

        aggregate_entry = {}

        try:
            timer_start = min(
                (v.get("timer_start") for k, v in existing_data.items()
                 if k.startswith("measurement_") and "timer_start" in v),
                default=None
            )
            timer_end = max(
                (v.get("timer_end") for k, v in existing_data.items()
                 if k.startswith("measurement_") and "timer_end" in v),
                default=None
            )
        except Exception:
            timer_start = timer_end = None

        if timer_start is not None:
            aggregate_entry["timer_start"] = timer_start
        if timer_end is not None:
            aggregate_entry["timer_end"] = timer_end

        if len(measurements_with_baseline) == 1:
            aggregate_entry["withBaseline"] = measurements_with_baseline[0]
            if measurements_without_baseline:
                aggregate_entry["withoutBaseline"] = measurements_without_baseline[0]
        else:
            aggregate_entry["withBaseline"] = self._aggregate_stats(
                measurements_with_baseline, timer_start, timer_end
            )
            if measurements_without_baseline:
                aggregate_entry["withoutBaseline"] = self._aggregate_stats(
                    measurements_without_baseline, timer_start, timer_end
                )

        existing_data["aggregate"] = aggregate_entry

    def _aggregate_stats(self, measurements, timer_start, timer_end):
        agg = {}
        all_events = set()
        for m in measurements:
            all_events.update(m.keys())

        for event in all_events:
            values = []
            for m in measurements:
                if event in m and "mean" in m[event]:
                    values.append(m[event]["mean"])
            if not values:
                continue

            arr = np.array(values)
            mean = np.mean(arr)
            event_data = {
                "unit": "W",
                "samples": len(arr),
                "min": round(float(np.min(arr)), 3),
                "max": round(float(np.max(arr)), 3),
                "mean": round(float(mean), 3),
                "std": round(float(np.std(arr)), 3),
                "percentiles": {
                    "p25": round(float(np.percentile(arr, 25)), 3),
                    "p50": round(float(np.percentile(arr, 50)), 3),
                    "p75": round(float(np.percentile(arr, 75)), 3),
                    "p90": round(float(np.percentile(arr, 90)), 3),
                    "p95": round(float(np.percentile(arr, 95)), 3),
                    "p99": round(float(np.percentile(arr, 99)), 3),
                },
            }

            delta_t = None
            if timer_start is not None and timer_end is not None:
                try:
                    delta_t = (int(timer_end) - int(timer_start)) / 1_000_000
                except Exception:
                    pass

            if delta_t is not None:
                event_data["consumption"] = round(float(mean * delta_t), 3)

            agg[event] = event_data

        return agg