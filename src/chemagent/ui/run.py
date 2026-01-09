"""Standalone script to launch ChemAgent Gradio UI."""

import argparse

from chemagent.ui import launch_app


def main():
    """Main entry point for Gradio UI."""
    parser = argparse.ArgumentParser(
        description="Launch ChemAgent Web Interface"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Server host (default: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Server port (default: 7860)"
    )
    
    parser.add_argument(
        "--share",
        action="store_true",
        help="Create public share link"
    )
    
    args = parser.parse_args()
    
    print(f"🚀 Launching ChemAgent Web UI on {args.host}:{args.port}")
    
    launch_app(
        server_name=args.host,
        server_port=args.port,
        share=args.share
    )


if __name__ == "__main__":
    main()
