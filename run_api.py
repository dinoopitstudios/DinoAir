#!/usr/bin/env python3
"""
Simple script to run the DinoAir API server
"""

import os
import sys
from pathlib import Path

# Add the API_files directory to Python path
api_dir = Path(__file__).parent / "API_files"
sys.path.insert(0, str(api_dir))

try:
    # Change to the API directory
    os.chdir(str(api_dir))

    import uvicorn

    config = uvicorn.Config(
        app="app:create_app",
        factory=True,
        host="127.0.0.1",
        port=24801,
        log_level="info",
        access_log=True,
        reload=False,
    )

    server = uvicorn.Server(config)
    server.run()

except ImportError:
    sys.exit(1)
except Exception:
    sys.exit(1)
