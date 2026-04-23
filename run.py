"""Mavuno Prototype Server Launcher."""
import uvicorn
import os

if __name__ == "__main__":
    # Point to port 8000 for Cloudflare tunnel compatibility
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=False)
