import argparse
import docker
import os
import sys


def run(game, state=None, entry=None, **kwargs):
    client = docker.from_env()
    remote_command = ['retro-challenge-remote', 'run', game, state, '-b', 'results/bk2', '-m', 'results']
    agent_command = ['retro-challenge-agent']

    if kwargs.get('wallclock_limit') is not None:
        remote_command.extend(['-W', str(kwargs['wallclock_limit'])])
    if kwargs.get('timestep_limit') is not None:
        remote_command.extend(['-T', str(kwargs['timestep_limit'])])
    if kwargs.get('discrete_actions'):
        remote_command.extend(['-D'])

    if entry:
        agent_command.append(entry)
        if kwargs.get('entry_args'):
            agent_command.extend(kwargs['entry_args'])

    if kwargs.get('resultsdir'):
        results = os.path.realpath(kwargs['resultsdir'])
    else:
        results = kwargs.get('resultsvol', 'compo-results')
    os.makedirs(results, exist_ok=True)

    container_kwargs = {'detach': True, 'network_disabled': True}

    client.volumes.create('compo-tmp-vol', driver='local', driver_opts={'type': 'tmpfs', 'device': 'tmpfs'})
    remote = client.containers.run('remote-env', remote_command,
                                   volumes={'compo-tmp-vol': {'bind': '/root/compo/tmp'},
                                            results: {'bind': '/root/compo/results'}},
                                   **container_kwargs)

    try:
        agent = client.containers.run('agent', agent_command,
                                      volumes={'compo-tmp-vol': {'bind': '/root/compo/tmp'}},
                                      runtime=kwargs.get('runtime', 'nvidia'),
                                      **container_kwargs)
    except:
        remote.kill()
        raise

    try:
        remote.wait()
    except KeyboardInterrupt:
        remote.kill()
    try:
        agent.wait(timeout=5)
    except requests.exceptions.ReadTimeout:
        agent.kill()

    logs = {
        'remote': (remote.logs(stdout=True), remote.logs(stderr=True)),
        'agent': (agent.logs(stdout=True), agent.logs(stderr=True))
    }

    remote.remove()
    agent.remove()
    if 'resultsdir' in kwargs:
        with open(os.path.join(results, 'remote-stdout.txt'), 'w') as f:
            f.write(logs['remote'][0].decode('utf-8'))
        with open(os.path.join(results, 'remote-stderr.txt'), 'w') as f:
            f.write(logs['remote'][1].decode('utf-8'))
        with open(os.path.join(results, 'agent-stdout.txt'), 'w') as f:
            f.write(logs['agent'][0].decode('utf-8'))
        with open(os.path.join(results, 'agent-stderr.txt'), 'w') as f:
            f.write(logs['agent'][1].decode('utf-8'))
    return logs


def run_args(args):
    kwargs = {
        'entry_args': args.args,
        'wallclock_limit': args.wallclock_limit,
        'timestep_limit': args.timestep_limit,
        'discrete_actions': args.discrete_actions,
        'resultsdir': args.results_dir,
    }

    if args.no_nv:
        kwargs['runtime'] = None

    run(args.game, args.state, args.entry, **kwargs)


def init_parser(parser):
    parser.set_defaults(func=run_args)
    parser.add_argument('game', type=str, help='Name of the game to run')
    parser.add_argument('state', type=str, default=None, nargs='?', help='Name of initial state')
    parser.add_argument('--entry', '-e', type=str, help='Name of agent entry point')
    parser.add_argument('--args', '-A', type=str, nargs='+', help='Extra agent entry arguments')
    parser.add_argument('--wallclock-limit', '-W', type=float, default=None, help='Maximum time to run in seconds')
    parser.add_argument('--timestep-limit', '-T', type=int, default=None, help='Maximum time to run in timesteps')
    parser.add_argument('--no-nv', '-N', action='store_true', help='Disable Nvidia runtime')
    parser.add_argument('--results-dir', '-r', type=str, help='Path to output results')
    parser.add_argument('--discrete-actions', '-D', action='store_true', help='Use a discrete action space')


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Run Retro Challenge support code')
    init_parser(parser)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == '__main__':
    main()
