import logging
from flask import Blueprint, request, jsonify
import json
from collections import defaultdict
from services.result_service import get_results_by_filters

logger = logging.getLogger(__name__)
result_blueprint = Blueprint("result", __name__)

def accumulate_event_sums(event_sums, event_counts, events):
    for event_name, event_data in events.items():
        if event_name not in event_sums:
            event_sums[event_name] = {
                "consumption": 0,
                "mean": 0,
                "min": 0,
                "max": 0,
                "std": 0,
                "carbon_footprint_g": 0
            }
            event_counts[event_name] = 0
        for k in event_sums[event_name]:
            event_sums[event_name][k] += event_data.get(k, 0)
        event_counts[event_name] += 1


def calculate_averages(event_sums, event_counts, delta_t_values=None):
    averages = {}
    allowed_keys = {"carbon_footprint_g", "consumption", "mean"}
    for event_name, sums in event_sums.items():
        count = event_counts[event_name] if event_counts[event_name] > 0 else 1
        averages[event_name] = {}
        for k, v in sums.items():
            if k not in allowed_keys:
                continue
            if k == "carbon_footprint_g":
                averages[event_name][k] = round(v / count, 6)
            else:
                averages[event_name][k] = round(v / count, 2)

    if delta_t_values:
        averages["delta_t_seconds"] = round(sum(delta_t_values) / len(delta_t_values), 2)

    return averages


def subtract_events(main_events, baseline_events):
    subtracted = {}
    for event_name, main_data in main_events.items():
        baseline_data = baseline_events.get(event_name)
        if baseline_data:
            subtracted[event_name] = {}
            for k, v in main_data.items():
                if isinstance(v, (int, float)):
                    subtracted[event_name][k] = v - baseline_data.get(k, 0)
                else:
                    subtracted[event_name][k] = v
        else:
            subtracted[event_name] = main_data.copy()
            subtracted[event_name]["no_baseline"] = True
    return subtracted


@result_blueprint.route("/wattsci", methods=["GET"])
def get_results_main():
    filters = {}
    for key in [
        "ci", "run_id", "branch", "repository", "workflow_id",
        "workflow_name", "commit_hash", "approach", "method", "label"
    ]:
        val = request.args.get(key)
        if val is not None:
            filters[key] = val.strip()

    if not filters:
        return jsonify({"error": "At least one filter parameter is required"}), 400

    try:
        results = get_results_by_filters(**filters)
        if not results:
            return jsonify({"error": "No results found"}), 404

        commits = defaultdict(lambda: {
            "measurements": [],
            "event_sums": {},
            "event_counts": {},
            "delta_t_values": []
        })

        for result in results:
            commit = result.commit_hash
            if result.json_main:
                try:
                    with open(result.json_main, "r", encoding="utf-8") as f:
                        main_content = json.load(f)
                        commits[commit]["measurements"].append(main_content)

                        if "delta_t_seconds" in main_content:
                            commits[commit]["delta_t_values"].append(main_content["delta_t_seconds"])

                        accumulate_event_sums(
                            commits[commit]["event_sums"],
                            commits[commit]["event_counts"],
                            main_content.get("events", {})
                        )
                except Exception as e:
                    logger.warning(f"Could not read JSON file {result.json_main}: {e}")

        output = {}
        for commit, data in commits.items():
            output[commit] = {
                "measurements": data["measurements"],
                "averages": calculate_averages(
                    data["event_sums"], data["event_counts"], data["delta_t_values"]
                )
            }

        print(output)

        return jsonify(output), 200

    except Exception as e:
        logger.error(f"Exception occurred while fetching results: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@result_blueprint.route("/wattsci/subtracted", methods=["GET"])
def get_results_subtracted():
    filters = {}
    for key in [
        "ci", "run_id", "branch", "repository", "workflow_id",
        "workflow_name", "commit_hash", "approach", "method", "label"
    ]:
        val = request.args.get(key)
        if val is not None:
            filters[key] = val.strip()

    if not filters:
        return jsonify({"error": "At least one filter parameter is required"}), 400

    try:
        results = get_results_by_filters(**filters)
        if not results:
            return jsonify({"error": "No results found"}), 404

        commits = defaultdict(list)
        output = {}

        for result in results:
            commits[result.commit_hash].append(result)

        for commit, results_in_commit in commits.items():
            if any(r.json_baseline is None for r in results_in_commit):
                return jsonify({"error": f"Not all measurements have baseline for commit {commit}"}), 400

            event_sums = {}
            event_counts = {}
            measurements = []
            delta_t_values = []

            for result in results_in_commit:
                main_content = baseline_content = None

                if result.json_main:
                    with open(result.json_main, "r", encoding="utf-8") as f:
                        main_content = json.load(f)

                if result.json_baseline:
                    with open(result.json_baseline, "r", encoding="utf-8") as f:
                        baseline_content = json.load(f)

                subtracted_events = subtract_events(
                    main_content.get("events", {}), baseline_content.get("events", {})
                )
                subtracted_measurement = main_content.copy()
                subtracted_measurement["events"] = subtracted_events
                measurements.append(subtracted_measurement)

                if "delta_t_seconds" in main_content:
                    delta_t_values.append(main_content["delta_t_seconds"])

                accumulate_event_sums(event_sums, event_counts, subtracted_events)

            output[commit] = {
                "measurements": measurements,
                "averages": calculate_averages(event_sums, event_counts, delta_t_values)
            }

        print(output)

        return jsonify(output), 200

    except Exception as e:
        logger.error(f"Exception occurred while fetching subtracted results: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500