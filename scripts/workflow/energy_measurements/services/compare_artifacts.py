def compare_artifacts(base_data, refactor_data):
    base_withBaseline = base_data.get("aggregate", {}).get("withBaseline", {})
    refactor_withBaseline = refactor_data.get("aggregate", {}).get("withBaseline", {})

    comparison = {}

    for metric, base_values in base_withBaseline.items():
        refactor_values = refactor_withBaseline.get(metric)
        if not refactor_values:
            comparison[metric] = {
                "base_consumption": base_values.get("consumption"),
                "refactor_consumption": None,
                "difference": None,
                "status": "missing_in_refactor",
                "base_carbon_footprint": base_values.get("carbon_footprint_g"),
                "refactor_carbon_footprint": None,
                "carbon_difference": None,
                "carbon_status": "missing_in_refactor"
            }
            continue

        base_consumption = base_values.get("consumption")
        refactor_consumption = refactor_values.get("consumption")

        base_carbon = base_values.get("carbon_footprint_g")
        refactor_carbon = refactor_values.get("carbon_footprint_g")

        diff = refactor_consumption - base_consumption if (base_consumption is not None and refactor_consumption is not None) else None
        status = (
            "improved" if diff is not None and diff < 0
            else "regressed" if diff is not None and diff > 0
            else "no_change" if diff == 0
            else "missing_consumption"
        )

        carbon_diff = refactor_carbon - base_carbon if (base_carbon is not None and refactor_carbon is not None) else None
        carbon_status = (
            "improved" if carbon_diff is not None and carbon_diff < 0
            else "regressed" if carbon_diff is not None and carbon_diff > 0
            else "no_change" if carbon_diff == 0
            else "missing_carbon_footprint"
        )

        comparison[metric] = {
            "base_consumption": base_consumption,
            "refactor_consumption": refactor_consumption,
            "difference": diff,
            "status": status,
            "base_carbon_footprint": base_carbon,
            "refactor_carbon_footprint": refactor_carbon,
            "carbon_difference": carbon_diff,
            "carbon_status": carbon_status
        }

    return {"withBaseline": comparison}
