import argparse
import docker
import io
import os
import random
import requests.exceptions
import sys
import tempfile
import threading
try:
    from retro import data_path
except ImportError:
    def data_path():
        raise RuntimeError('Could not find Gym Retro data directory')


class LogThread:
    def __init__(self, container):
        self._log = container.logs(stdout=True, stderr=True, stream=True)
        self._thread = threading.Thread(target=self._run)
        self._active = False

    def start(self):
        if self._active:
            return
        self._active = True
        self._thread.start()

    def exit(self):
        self._active = False

    def _run(self):
        while self._active:
            try:
                print(next(self._log).decode('utf-8'), end='')
            except StopIteration:
                break


def run(game, state=None, entry=None, **kwargs):
    client = docker.from_env()
    remote_command = ['retro-contest-remote', 'run', game, *([state] if state else []), '-b', 'results/bk2', '-m', 'results']
    agent_command = []
    agent_name = kwargs.get('agent', 'agent')
    datamount = {}

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

    rand = ''.join(random.sample('abcdefghijklmnopqrstuvwxyz0123456789', 8))
    bridge = client.volumes.create('compo-tmp-vol-%s' % rand, driver='local', driver_opts={'type': 'tmpfs', 'device': 'tmpfs'})
    if kwargs.get('use_host_data'):
        remote_command = [remote_command[0], '--data-dir', '/root/data', *remote_command[1:]]
        datamount = {data_path(): {'bind': '/root/data', 'mode': 'ro'}}

    remote = client.containers.run('remote-env', remote_command,
                                   volumes={'compo-tmp-vol-%s' % rand: {'bind': '/root/compo/tmp'},
                                            results: {'bind': '/root/compo/results'},
                                            **datamount},
                                   **container_kwargs)

    try:
        agent = client.containers.run(agent_name, agent_command,
                                      volumes={'compo-tmp-vol-%s' % rand: {'bind': '/root/compo/tmp'}},
                                      runtime=kwargs.get('runtime', 'nvidia'),
                                      **container_kwargs)
    except:
        remote.kill()
        raise

    a_exit = None
    r_exit = None

    if not kwargs.get('quiet'):
        log_thread = LogThread(agent)
        log_thread.start()

    try:
        while True:
            try:
                a_exit = agent.wait(timeout=5)
                break
            except requests.exceptions.RequestException:
                pass
            try:
                r_exit = remote.wait(timeout=5)
                break
            except requests.exceptions.RequestException:
                pass

        if a_exit is None:
            try:
                a_exit = agent.wait(timeout=1)
            except requests.exceptions.RequestException:
                agent.kill()
        if r_exit is None:
            try:
                r_exit = remote.wait(timeout=1)
            except requests.exceptions.RequestException:
                remote.kill()
    except:
        if a_exit is None:
            try:
                a_exit = agent.wait(timeout=0.2)
            except:
                try:
                    agent.kill()
                except docker.errors.APIError:
                    pass
        if r_exit is None:
            try:
                r_exit = remote.wait(timeout=0.2)
            except:
                try:
                    remote.kill()
                except docker.errors.APIError:
                    pass
        raise
    finally:
        if isinstance(a_exit, dict):
            a_exit = a_exit.get('StatusCode')
        if isinstance(r_exit, dict):
            r_exit = r_exit.get('StatusCode')

        if not kwargs.get('quiet'):
            log_thread.exit()

        logs = {
            'remote': (r_exit, remote.logs(stdout=True, stderr=False), remote.logs(stdout=False, stderr=True)),
            'agent': (a_exit, agent.logs(stdout=True, stderr=False), agent.logs(stdout=False, stderr=True))
        }

        if 'resultsdir' in kwargs:
            with open(os.path.join(results, 'remote-stdout.txt'), 'w') as f:
                f.write(logs['remote'][1].decode('utf-8'))
            with open(os.path.join(results, 'remote-stderr.txt'), 'w') as f:
                f.write(logs['remote'][2].decode('utf-8'))
            with open(os.path.join(results, 'agent-stdout.txt'), 'w') as f:
                f.write(logs['agent'][1].decode('utf-8'))
            with open(os.path.join(results, 'agent-stderr.txt'), 'w') as f:
                f.write(logs['agent'][2].decode('utf-8'))

        remote.remove()
        agent.remove()
        bridge.remove()

    return logs


def run_args(args):
    kwargs = {
        'entry_args': args.args,
        'wallclock_limit': args.wallclock_limit,
        'timestep_limit': args.timestep_limit,
        'discrete_actions': args.discrete_actions,
        'resultsdir': args.results_dir,
        'quiet': args.quiet,
        'use_host_data': args.use_host_data,
    }

    if args.no_nv:
        kwargs['runtime'] = None

    if args.agent:
        kwargs['agent'] = args.agent

    results = run(args.game, args.state, args.entry, **kwargs)
    if results['remote'][0] or results['agent'][0]:
        if results['remote'][0]:
            print('Remote exited uncleanly:', results['remote'][0])
        if results['agent'][0]:
            print('Agent exited uncleanly', results['agent'][0])
        sys.exit(1)


def build(path, tag, install=None, pass_env=False):
    from pkg_resources import EntryPoint
    import tarfile
    if install:
        destination = 'module'
    else:
        destination = 'agent.py'
    docker_file = ['FROM openai/retro-agent',
                   'COPY context %s' % destination]

    if not install:
        docker_file.append('CMD ["python", "-u", "/root/compo/agent.py"]')
    else:
        docker_file.append('RUN . ~/venv/bin/activate && pip install -e module')
        valid = not any(c in install for c in ' "\\')
        if pass_env:
            try:
                EntryPoint.parse('entry=' + install)
            except ValueError:
                valid = False
            if not valid:
                raise ValueError('Invalid entry point')
            docker_file.append('CMD ["retro-contest-agent", "%s"]' % install)
        else:
            if not valid:
                raise ValueError('Invalid module name')
            docker_file.append('CMD ["python", "-u", "-m", "%s"]' % install)

    print('Creating Docker image...')
    docker_file_full = io.BytesIO('\n'.join(docker_file).encode('utf-8'))
    client = docker.from_env()
    with tempfile.NamedTemporaryFile() as f:
        tf = tarfile.open(mode='w:gz', fileobj=f)
        docker_file_info = tarfile.TarInfo('Dockerfile')
        docker_file_info.size = len(docker_file_full.getvalue())
        tf.addfile(docker_file_info, docker_file_full)
        tf.add(path, arcname='context', exclude=lambda fname: fname.endswith('/.git'))
        tf.close()
        f.seek(0)
        client.images.build(fileobj=f, custom_context=True, tag=tag, gzip=True)
    print('Done!')


def build_args(args):
    kwargs = {
        'install': args.install,
        'pass_env': args.pass_env,
    }

    try:
        build(args.path, args.tag, **kwargs)
    except docker.errors.BuildError as be:
        print(*[log['stream'] for log in be.build_log if 'stream' in log])
        raise


def init_parser(subparsers):
    parser_run = subparsers.add_parser('run', description='Run Docker containers locally')
    parser_run.set_defaults(func=run_args)
    parser_run.add_argument('game', type=str, help='Name of the game to run')
    parser_run.add_argument('state', type=str, default=None, nargs='?', help='Name of initial state')
    parser_run.add_argument('--entry', '-e', type=str, help='Name of agent entry point')
    parser_run.add_argument('--args', '-A', type=str, nargs='+', help='Extra agent entry arguments')
    parser_run.add_argument('--agent', '-a', type=str, help='Extra agent Docker image')
    parser_run.add_argument('--wallclock-limit', '-W', type=float, default=None, help='Maximum time to run in seconds')
    parser_run.add_argument('--timestep-limit', '-T', type=int, default=None, help='Maximum time to run in timesteps')
    parser_run.add_argument('--no-nv', '-N', action='store_true', help='Disable Nvidia runtime')
    parser_run.add_argument('--results-dir', '-r', type=str, help='Path to output results')
    parser_run.add_argument('--discrete-actions', '-D', action='store_true', help='Use a discrete action space')
    parser_run.add_argument('--use-host-data', '-d', action='store_true', help='Use the host Gym Retro data directory')
    parser_run.add_argument('--quiet', '-q', action='store_true', help='Disable printing agent logs')

    parser_build = subparsers.add_parser('build', description='Build agent Docker containers')
    parser_build.set_defaults(func=build_args)
    parser_build.add_argument('path', type=str, help='Path to a file or package')
    parser_build.add_argument('--tag', '-t', required=True, type=str, help='Tag name for the built image')
    parser_build.add_argument('--install', '-i', type=str, help='Install as a package and run specified module or entry point (if -e is specified)')
    parser_build.add_argument('--pass-env', '-e', action='store_true', help='Pass preconfigured environment to entry point specified by -i')


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Run OpenAI Retro Contest support code')
    init_parser(parser)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == '__main__':
    main()
