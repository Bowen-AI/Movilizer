"""Serve the generated website/public directory locally."""

from __future__ import annotations

import argparse
import os
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run local static website server")
    p.add_argument("--website_dir", default="website")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    public_dir = Path(args.website_dir) / "public"
    public_dir.mkdir(parents=True, exist_ok=True)

    os.chdir(public_dir)
    server = ThreadingHTTPServer((args.host, args.port), SimpleHTTPRequestHandler)
    print(f"Serving {public_dir.resolve()} at http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
