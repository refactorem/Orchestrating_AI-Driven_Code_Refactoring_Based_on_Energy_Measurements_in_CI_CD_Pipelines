import logging
import json
import requests

logger = logging.getLogger(__name__)

def fetch_carbon_intensity():
    url = "https://api.electricitymap.org/v3/carbon-intensity/latest"
    headers = {"auth-token": "yz4qkEc4LG63XC5G8Bq3"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def add_carbon_footprint(data: dict, carbon_intensity: float):
    events = data.get("events", {})
    for event_name, event_data in events.items():
        if isinstance(event_data, dict) and "consumption" in event_data:
            try:
                consumption_joules = event_data["consumption"]
                consumption_kwh = consumption_joules / 3_600_000
                carbon_footprint_g = consumption_kwh * carbon_intensity
                event_data["carbon_footprint_g"] = round(carbon_footprint_g, 6)
            except Exception as e:
                logger.warning(f"Error calculando huella para {event_name}: {e}")

def enrich_json_with_carbon_data(json_path: str, carbon_intensity: float):
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["carbon_intensity"] = carbon_intensity
        add_carbon_footprint(data, carbon_intensity)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info("JSON enriquecido con huella de carbono")
    except Exception as e:
        logger.error(f"Error enriqueciendo JSON con datos de carbono: {e}", exc_info=True)
