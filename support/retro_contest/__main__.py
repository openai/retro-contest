import argparse
import sys

try:
    import retro_contest.docker as docker_cmd
except ImportError:
    docker_cmd = None

try:
    import retro_contest.rest as rest_cmd
except ImportError:
    rest_cmd = None


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Run OpenAI Retro Contest support code')
    parser.set_defaults(func=lambda args: parser.print_help())
    subparsers = parser.add_subparsers()
    if docker_cmd:
        docker_cmd.init_parser(subparsers)
    if rest_cmd:
        rest_cmd.init_parsers(subparsers)

    args = parser.parse_args(argv)
    if not args.func(args):
        sys.exit(1)


if __name__ == '__main__':
    main()
