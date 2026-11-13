import uvicorn
import os
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(root_dir))

# Configure Matplotlib config dir to prevent permission issues
mpl_dir = root_dir / "config" / "matplotlib"
mpl_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(mpl_dir))

# Automatically load local .env credentials
try:
    from dotenv import load_dotenv
    load_dotenv(root_dir / ".env")
except ImportError:
    pass

PORT = int(os.environ.get("SCHOLARFORGE_PORT", os.environ.get("PORT", 8008)))
HOST = os.environ.get("HOST", "127.0.0.1")

if __name__ == "__main__":
    print("=" * 60)
    print("SCHOLARFORGE OS: LAUNCHING LOCAL API & WORKSPACE SERVER")
    print(f"API Endpoint: http://localhost:{PORT}")
    print(f"Documentation & OpenAPI: http://localhost:{PORT}/docs")
    print("=" * 60)
    uvicorn.run("scholarforge.api.main:app", host=HOST, port=PORT, reload=False)
