# pcm.py
import os

class pcm:
    def __init__(self, session_dir: str, original_name: str):
        self.session_dir = session_dir
        self.original_name = original_name

    def process(self) -> str:
        processed_file = os.path.join(self.session_dir, f"processed_{self.original_name}")
        with open(processed_file, "w") as f:
            f.write("PCM processing result (simulated)\n")
        return processed_file
