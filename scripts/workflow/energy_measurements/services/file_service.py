import os
import hashlib
import gzip
import shutil

BASE_UPLOAD_DIR = os.path.join(os.path.expanduser("~"), "cimeasurement", "uploads")
os.makedirs(BASE_UPLOAD_DIR, exist_ok=True)

IDENTIFYING_FIELDS = [
    'CI',
    'RUN_ID',
    'REF_NAME',
    'REPOSITORY',
    'WORKFLOW_ID',
    'WORKFLOW_NAME',
    'COMMIT_HASH',
    'APPROACH',
    'METHOD',
    'LABEL'
]

def get_combined_id(form):
    combined_str = "|".join(form.get(f, "") for f in IDENTIFYING_FIELDS)
    return hashlib.sha256(combined_str.encode()).hexdigest()

def get_session_dir_by_form(form):
    session_id = get_combined_id(form)
    session_dir = os.path.join(BASE_UPLOAD_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)
    return session_dir, session_id

def reconstruct_file_from_chunks(base_dir):
    chunks_dir = os.path.join(base_dir, "chunks")
    os.makedirs(chunks_dir, exist_ok=True)

    chunks = sorted(f for f in os.listdir(chunks_dir) if "chunk" in f)
    if not chunks:
        raise Exception("No chunks found in chunks/")

    compressed_path = os.path.join(base_dir, "reconstructed.gz")
    with open(compressed_path, "wb") as out_f:
        for chunk_name in chunks:
            chunk_path = os.path.join(chunks_dir, chunk_name)
            with open(chunk_path, "rb") as c:
                out_f.write(c.read())

    decompressed_path = os.path.join(base_dir, "decompressed")
    with gzip.open(compressed_path, "rb") as f_in, open(decompressed_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

    return decompressed_path

def cleanup_chunks_files(session_dir):
    for f in os.listdir(session_dir):
        file_path = os.path.join(session_dir, f)
        if os.path.isfile(file_path) and (f.endswith(".gz") or "chunk" in f):
            os.remove(file_path)
