"""
CLI entry point for the MovieStudioDaemon.
Run with: python -m studio.daemon [OPTIONS]
"""

import argparse
import sys
from pathlib import Path

from studio.daemon import MovieStudioDaemon


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Movilizer Movie Studio Daemon - Autonomous AI Movie Generation'
    )
    parser.add_argument(
        '--config',
        type=Path,
        default=None,
        help='Path to daemon configuration YAML file',
    )
    parser.add_argument(
        '--prompt',
        type=str,
        default=None,
        help='Single prompt to process and exit (single_movie mode)',
    )
    parser.add_argument(
        '--mode',
        type=str,
        choices=['continuous', 'single_movie'],
        default='continuous',
        help='Run mode: continuous (default) or single_movie',
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Print daemon status and exit',
    )

    args = parser.parse_args()

    # Create daemon
    daemon = MovieStudioDaemon(config_path=args.config)

    # Handle status query
    if args.status:
        try:
            status = daemon.get_status()
            print("Daemon Status:")
            print(f"  Running: {status['running']}")
            print(f"  Active movies: {status['active_movies']}")
            print(f"  Completed movies: {status['completed_movies']}")
            print(f"  Queue size: {status['queue_size']}")
            print(f"  Active tasks: {status['active_tasks']}")
        except Exception as e:
            print(f"Error: {e}")
        return 0

    # Start daemon
    daemon.start()

    try:
        # Handle single movie mode
        if args.mode == 'single_movie':
            if not args.prompt:
                print("Error: --prompt is required in single_movie mode")
                daemon.shutdown()
                return 1

            movie_id = daemon.add_prompt(args.prompt)
            print(f"Processing: {args.prompt}")
            print(f"Movie ID: {movie_id}")

            # Wait for completion (max 300 seconds)
            for _ in range(300):
                movie = daemon.state_manager.get_movie(movie_id)
                if movie and movie.status.value == 'PUBLISHED':
                    print(f"SUCCESS: Movie published!")
                    break
                import time
                time.sleep(1)

            daemon.shutdown()
            return 0

        # Continuous mode - run forever
        print("Daemon running in continuous mode (press Ctrl+C to stop)")
        import time
        try:
            while daemon._running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    finally:
        daemon.shutdown()

    return 0


if __name__ == '__main__':
    sys.exit(main())
