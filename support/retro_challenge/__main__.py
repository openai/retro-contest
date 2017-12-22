import argparse
import sys

try:
    import retro_challenge.docker as docker_cmd
except ImportError:
    docker_cmd = None

try:
    import retro_challenge.rest as rest_cmd
except ImportError:
    rest_cmd = None


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Run Retro Challenge support code')
    parser.set_defaults(func=lambda args: parser.print_help())
    subparsers = parser.add_subparsers()
    if docker_cmd:
        parser_run = subparsers.add_parser('run', description='Run Docker containers')
        docker_cmd.init_parser(parser_run)
    if rest_cmd:
        rest_cmd.init_parsers(subparsers)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == '__main__':
    main()
