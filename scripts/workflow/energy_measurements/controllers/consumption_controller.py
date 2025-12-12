import logging
from flask import Blueprint, request, jsonify
from services.result_service import get_results_by_repo_branch

logger = logging.getLogger(__name__)
consumption_blueprint = Blueprint("consumption", __name__)

@consumption_blueprint.route("/wattsci/consumption", methods=["GET"])
def get_consumption():
    repo = request.args.get("repo")
    branch = request.args.get("branch")

    if not all([repo, branch]):
        logger.warning("Missing required query parameters for consumption endpoint")
        return jsonify({"error": "Missing required query parameters"}), 400

    try:
        logger.info(f"Fetching consumption results for repo={repo}, branch={branch}")
        results = get_results_by_repo_branch(repo, branch)
        return jsonify({"results": results})
    except Exception as e:
        logger.error(f"Error fetching consumption results: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
