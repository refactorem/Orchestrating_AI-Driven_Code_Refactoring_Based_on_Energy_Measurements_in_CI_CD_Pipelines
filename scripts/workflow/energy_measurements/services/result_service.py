import json
from models.result import Result
from db.db import db_session


def save_result(session_id, json_path, upload_fields):
    result = Result(
        session_id=session_id,
        repository=upload_fields.get("WATTSCI_REPOSITORY"),
        branch=upload_fields.get("WATTSCI_BRANCH"),
        workflow_id=upload_fields.get("WATTSCI_WORKFLOW_ID"),
        workflow_name=upload_fields.get("WATTSCI_WORKFLOW_NAME"),
        commit_hash=upload_fields.get("WATTSCI_COMMIT_HASH"),
        method=upload_fields.get("WATTSCI_METHOD"),
        json_path=json_path
    )
    db_session.add(result)
    db_session.commit()
    return result

def get_results_by_repo_branch(repo, branch):
    repo = repo.strip()
    branch = branch.strip()

    results = db_session.query(Result).filter(
        Result.repository == repo,
        Result.branch == branch
    ).all()

    output = []

    for result in results:
        try:
            with open(result.json_path, "r") as f:
                json_content = json.load(f)

            aggregate = json_content.get("aggregate", {})

            with_baseline_data = aggregate.get("withBaseline", {})
            with_baseline = {
                metric: data.get("consumption")
                for metric, data in with_baseline_data.items()
                if isinstance(data, dict) and "consumption" in data
            }

            without_baseline_data = aggregate.get("withoutBaseline", {})
            without_baseline = {
                metric: data.get("consumption")
                for metric, data in without_baseline_data.items()
                if isinstance(data, dict) and "consumption" in data
            }

            output.append({
                "id": result.id,
                "session_id": result.session_id,
                "commit_hash": result.commit_hash,
                "workflow_id": result.workflow_id,
                "created_at": result.created_at.isoformat(),
                "withBaseline": with_baseline,
                "withoutBaseline": without_baseline
            })

        except Exception as e:
            continue

    return output


def get_results_by_filters(
    ci=None,
    run_id=None,
    branch=None,
    repository=None,
    workflow_id=None,
    workflow_name=None,
    commit_hash=None,
    approach=None,
    method=None,
    label=None
):
    query = db_session.query(Result)

    if ci is not None:
        query = query.filter(Result.ci == ci)
    if run_id is not None:
        query = query.filter(Result.run_id == run_id)
    if branch is not None:
        query = query.filter(Result.branch == branch)
    if repository is not None:
        query = query.filter(Result.repository == repository)
    if workflow_id is not None:
        query = query.filter(Result.workflow_id == workflow_id)
    if workflow_name is not None:
        query = query.filter(Result.workflow_name == workflow_name)
    if commit_hash is not None:
        query = query.filter(Result.commit_hash == commit_hash)
    if approach is not None:
        query = query.filter(Result.approach == approach)
    if method is not None:
        query = query.filter(Result.method == method)
    if label is not None:
        query = query.filter(Result.label == label)

    return query.all()
