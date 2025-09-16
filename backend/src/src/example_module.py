import os
from venture_os.repo.jsonl import JsonlEntityRepo

# Other imports and code

# repo selection (memory by default; opt-in JSONL via env)
_store = os.environ.get("VOS_STORE", "memory").lower()
if _store == "jsonl":
    _path = os.environ.get("VOS_STORE_PATH", "data/venture_os.jsonl")
    os.makedirs(os.path.dirname(_path), exist_ok=True)
    _repo = JsonlEntityRepo(_path)
else:
    _repo = MemoryEntityRepo()

# Rest of the code
