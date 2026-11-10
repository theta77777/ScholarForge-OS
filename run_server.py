import uvicorn
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

PORT = int(os.environ.get("SCHOLARFORGE_PORT", 8008))

if __name__ == "__main__":
    print("=" * 60)
    print("SCHOLARFORGE OS: LAUNCHING LOCAL API & WORKSPACE SERVER")
    print(f"API Endpoint: http://localhost:{PORT}")
    print(f"Documentation & OpenAPI: http://localhost:{PORT}/docs")
    print("=" * 60)
    uvicorn.run("scholarforge.api.main:app", host="127.0.0.1", port=PORT, reload=False)
