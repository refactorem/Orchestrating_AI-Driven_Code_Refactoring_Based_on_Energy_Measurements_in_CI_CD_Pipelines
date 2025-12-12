import logging
from flask import Blueprint, json, request, jsonify
import os
from services.file_service import get_session_dir_by_form, reconstruct_file_from_chunks, BASE_UPLOAD_DIR
from models.result import Result
from db.db import db_session
from methods.runner import MethodRunner
from db.db import db_session
from models.result import Result

logger = logging.getLogger(__name__)
upload_blueprint = Blueprint("upload", __name__)

@upload_blueprint.route("/upload", methods=["POST"])
def upload_chunk():
    session_dir, session_id = get_session_dir_by_form(request.form)
    chunk = request.files.get("chunk")
    chunk_name = request.form.get("chunk_name")
    chunk_type = request.form.get("type", "main")
    
    timer_start = request.form.get("timer_start")
    timer_end = request.form.get("timer_end")

    if not chunk or not chunk_name:
        logger.warning("Upload chunk missing file or chunk_name")
        return jsonify({"error": "Missing file or chunk_name"}), 400

    chunks_dir = os.path.join(session_dir, chunk_type, "chunks")
    os.makedirs(chunks_dir, exist_ok=True)

    chunk_path = os.path.join(chunks_dir, chunk_name)
    try:
        chunk.save(chunk_path)
        logger.info(f"Chunk {chunk_name} saved for session {session_id} in {chunk_type}")

        if timer_start and timer_end:
            data_dir = os.path.join(session_dir, chunk_type, "data")
            os.makedirs(data_dir, exist_ok=True)
            with open(os.path.join(data_dir, "timer_start.txt"), "w") as f:
                f.write(timer_start)
            with open(os.path.join(data_dir, "timer_end.txt"), "w") as f:
                f.write(timer_end)
            logger.info(f"Timestamps saved in {data_dir} for session {session_id}")

    except Exception as e:
        logger.error(f"Failed to save chunk {chunk_name} for session {session_id}: {e}")
        return jsonify({"error": "Failed to save chunk"}), 500

    return jsonify({
        "status": "received",
        "chunk": chunk_name,
        "session_id": session_id,
        "type": chunk_type,
        "timer_start": timer_start,
        "timer_end": timer_end,
        "chunks_path": chunks_dir,
        "data_path": data_dir if timer_start else None
    }), 200

@upload_blueprint.route("/reconstruct", methods=["POST"])
def reconstruct():
    session_id = request.form.get("session_id")
    if not session_id:
        logger.warning("Reconstruct called without session_id")
        return jsonify({"error": "Missing session_id"}), 400

    session_dir = os.path.join(BASE_UPLOAD_DIR, session_id)
    ci = request.form.get("CI")
    run_id = request.form.get("RUN_ID")
    branch = request.form.get("REF_NAME")
    repository = request.form.get("REPOSITORY")
    workflow_id = request.form.get("WORKFLOW_ID")
    workflow_name = request.form.get("WORKFLOW_NAME")
    commit_hash = request.form.get("COMMIT_HASH")
    approach = request.form.get("APPROACH")
    method = request.form.get("METHOD")
    label = request.form.get("LABEL")

    try:
        logger.info(f"Starting reconstruction for session {session_id}")

        json_baseline_path = None
        baseline_chunks_dir = os.path.join(session_dir, "baseline")
        if os.path.exists(baseline_chunks_dir):
            path = reconstruct_file_from_chunks(baseline_chunks_dir)
            runner_baseline = MethodRunner(approach, method, baseline_chunks_dir, path)
            json_baseline_path = runner_baseline.run()

        json_main_path = None
        main_chunks_dir = os.path.join(session_dir, "main")
        if os.path.exists(main_chunks_dir):
            path = reconstruct_file_from_chunks(main_chunks_dir)
            runner_main = MethodRunner(approach, method, main_chunks_dir, path)
            json_main_path = runner_main.run()

        result = Result(
            session_id=session_id,
            ci=ci,
            run_id=run_id,
            branch=branch,
            repository=repository,
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            commit_hash=commit_hash,
            approach=approach,
            method=method,
            label=label,
            json_main=json_main_path,
            json_baseline=json_baseline_path
        )
        db_session.add(result)
        db_session.commit()

        return jsonify({
            "session_id": session_id,
            "status": "success",
            "result_id": result.id,
            "json_main": json_main_path,
            "json_baseline": json_baseline_path
        }), 200

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error during reconstruction for session {session_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to reconstruct file", "details": str(e)}), 500
