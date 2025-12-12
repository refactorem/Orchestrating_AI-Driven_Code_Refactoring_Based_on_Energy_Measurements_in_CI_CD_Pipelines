import json
import logging
import requests
import urllib.parse
from flask import Blueprint, request, jsonify
from models.result import Result
from db.db import db_session
from services.compare_artifacts import compare_artifacts

logger = logging.getLogger(__name__)
compare_blueprint = Blueprint("compare", __name__)


def create_pull_request(repo, base_branch, refactor_branch, github_token, head_owner=None):
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    owner, repo_name = repo.split("/")
    if head_owner is None:
        head_owner = owner

    repo_api = f"https://api.github.com/repos/{repo}"

    head = refactor_branch if head_owner == owner else f"{head_owner}:{refactor_branch}"

    existing_prs_url = f"{repo_api}/pulls?head={head}&base={base_branch}"
    existing_response = requests.get(existing_prs_url, headers=headers)
    if existing_response.status_code == 200 and existing_response.json():
        logger.info("Pull request already exists.")
        return existing_response.json()[0]["number"]

    data = {
        "title": "GreenCodeRefactor",
        "head": head,
        "base": base_branch,
        "body": "This PR was created automatically to compare energy performance."
    }

    print("=== DEBUG: Creating PR with the following data ===")
    print(f"POST URL: {repo_api}/pulls")
    print(f"Headers: {headers}")
    print("Payload JSON:")
    print(json.dumps(data, indent=2))
    print("============================================")

    response = requests.post(f"{repo_api}/pulls", headers=headers, json=data)

    if response.status_code == 201:
        logger.info("Pull request created successfully.")
        return response.json()["number"]
    else:
        logger.error(f"Failed to create PR: {response.status_code} - {response.text}")
        return None


def post_comparison_comment(repo, pr_number, github_token, comparison_data):
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json"
    }

    if "comparison" in comparison_data:
        comparison = comparison_data["comparison"]
    else:
        comparison = comparison_data

    data_key = None
    if "withBaseline" in comparison:
        data_key = "withBaseline"
    elif "withoutBaseline" in comparison:
        data_key = "withoutBaseline"
    else:
        logger.error("No valid comparison data found (withBaseline or withoutBaseline).")
        return

    data_section = comparison[data_key]

    def get_color(value):
        return "green" if value < 0 else "red"

    def make_badge(label, message, color):
        label_safe = urllib.parse.quote(label, safe='')
        message_safe = urllib.parse.quote(message, safe='')
        return f"![{label}](https://img.shields.io/badge/{label_safe}-{message_safe}-{color})"

    base_lines = []
    refactor_lines = []
    summary_lines = []

    for key, vals in data_section.items():
        base_cons = vals.get("base_consumption", None)
        refactor_cons = vals.get("refactor_consumption", None)
        base_carb = vals.get("base_carbon_footprint", None)
        refactor_carb = vals.get("refactor_carbon_footprint", None)
        diff_cons = vals.get("difference", None)
        diff_carb = vals.get("carbon_difference", None)

        if base_cons is not None:
            base_lines.append(f"`{key} base_consumption`: {base_cons:.3f} J")
        if base_carb is not None:
            base_lines.append(f"`{key} base_carbon_footprint`: {base_carb:.6f} g")

        if refactor_cons is not None:
            refactor_lines.append(f"`{key} refactor_consumption`: {refactor_cons:.3f} J")
        if refactor_carb is not None:
            refactor_lines.append(f"`{key} refactor_carbon_footprint`: {refactor_carb:.6f} g")

        if diff_cons is not None:
            color = get_color(diff_cons)
            sign = "+" if diff_cons > 0 else ""
            value_badge = make_badge("", f"{sign}{diff_cons:.3f}J", color)
            summary_lines.append(f"**{key}**: {value_badge}")
        if diff_carb is not None:
            color = get_color(diff_carb)
            sign = "+" if diff_carb > 0 else ""
            value_badge = make_badge("", f"{sign}{diff_carb:.6f}g", color)
            summary_lines.append(f"**{key}**: {value_badge}")

    base_text = "  \n".join(base_lines)
    refactor_text = "  \n".join(refactor_lines)
    summary_text = "  \n".join(summary_lines)

    comment_body = f"""
### Base:
{base_text}

### Refactor:
{refactor_text}

### Summary:
{summary_text}

---

*Note: Green = Improvement (decrease), Red = Regression (increase)*
"""

    comment_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    response = requests.post(comment_url, headers=headers, json={"body": comment_body})

    if response.status_code == 201:
        logger.info("Comment posted to PR.")
    else:
        logger.error(f"Failed to comment on PR: {response.status_code} - {response.text}")



@compare_blueprint.route("/wattsci/compare", methods=["POST"])
def compare_results():
    repo = request.form.get("repo")
    base_branch = request.form.get("base_branch")
    refactor_branch = request.form.get("refactor_branch")
    github_token = request.form.get("github_token")

    if not all([repo, base_branch, refactor_branch, github_token]):
        logger.warning("Missing required query parameters for compare endpoint")
        return jsonify({
            "error": "Missing required parameters: repo, base_branch, refactor_branch, github_token"
        }), 400

    try:
        repo = repo.strip()
        base_branch = base_branch.strip()
        refactor_branch = refactor_branch.strip()
        github_token = github_token.strip()

        print(repo, base_branch, refactor_branch )

        base_result = (
            db_session.query(Result)
            .filter(Result.repository == repo, Result.branch == base_branch)
            .order_by(Result.created_at.desc())
            .first()
        )
        refactor_result = (
            db_session.query(Result)
            .filter(Result.repository == repo, Result.branch == refactor_branch)
            .order_by(Result.created_at.desc())
            .first()
        )

        if not base_result or not refactor_result:
            msg = "Results not found for given base_branch or refactor_branch"
            logger.warning(msg)
            return jsonify({"error": msg}), 404

        with open(base_result.json_path, "r") as f:
            base_data = json.load(f)
        with open(refactor_result.json_path, "r") as f:
            refactor_data = json.load(f)

        comparison = compare_artifacts(base_data, refactor_data)

        pr_number = create_pull_request(repo, base_branch, refactor_branch, github_token)
        if pr_number:
            post_comparison_comment(repo, pr_number, github_token, comparison)

        return jsonify({"comparison": comparison})

    except Exception as e:
        logger.error(f"Error in compare_results: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
