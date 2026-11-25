"""Development entry point. Use waitress-serve for deployed instances."""
import argparse
from wsgiref.simple_server import make_server
from app import application

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local development server (not for public deployment)")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    with make_server("127.0.0.1", args.port, application) as server:
        print(f"Development server: http://127.0.0.1:{args.port}", flush=True)
        server.serve_forever()
