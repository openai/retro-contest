import argparse
import docker
import getpass
import itertools
import json
import os
import requests
import sys
import yaml
from functools import wraps
from requests.auth import HTTPBasicAuth

config = {}


def update_config(key, value):
    config[key] = value
    write_config()


def clear_config(key):
    del config[key]
    write_config()


def write_config():
    os.makedirs(os.path.join(os.path.expanduser('~'), '.config'), exist_ok=True)
    c = yaml.dump(config, default_flow_style=False)
    with open(os.path.join(os.path.expanduser('~'), '.config/retro-contest.yml'), 'w') as f:
        f.write(c)


def load_config():
    global config
    try:
        with open(os.path.join(os.path.expanduser('~'), '.config/retro-contest.yml')) as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        pass


def login(email, password, server=None):
    if not server:
        server = config.get('server')
    if server and not (server.startswith('http://') or server.startswith('https://')):
        server = 'http://' + server
    r = requests.post(server + '/rest/login', json={'email': email, 'password': password})
    if r.status_code // 100 == 2:
        update_config('cookies', dict(r.cookies))
        update_config('server', server)
        return True
    return False


def login_args(args):
    email = args.email
    if not email:
        email = input('Email address: ')
    password = args.password
    if args.password_stdin or not password:
        password = getpass.getpass()
    server = args.server
    if login(email, password, server):
        print('Login succeeded')
    else:
        print('Login failed')
        return False
    return True


def leaderboard_args(args):
    server = config.get('server')
    r = requests.get(server + '/rest/leaderboard')
    if r.status_code // 100 == 2:
        try:
            info = r.json()
            board = info.get('leaderboard')
        except:
            return
        for place, score in zip(itertools.count(info.get('start', 1)), board):
            print('#%i:' % place)
            print('- User:', score['name'])
            print('- Score:', score['score'])
    else:
        return False
    return True


def logout_args(args):
    clear_config('cookies')
    print('Logged out')
    return True


def needs_login(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        server = config.get('server')
        cookies = config.get('cookies')
        if not server or not cookies:
            print('You are not logged in')
            return None
        return f(server=server, cookies=cookies, *args, **kwargs)
    return wrapped


@needs_login
def docker_login_args(args, server, cookies):
    r = requests.get(server + '/rest/user', cookies=cookies)
    if r.status_code != 200 or 'cr' not in r.json():
        print('Failed to obtain container registry')
        return False
    cr = r.json()['cr']
    client = docker.from_env()
    client.login(cr['username'], cr['password'], registry=cr['url'])
    print('Logged in')
    return True


@needs_login
def docker_show_args(args, server, cookies):
    r = requests.get(server + '/rest/user', cookies=cookies)
    if r.status_code != 200 or 'cr' not in r.json():
        print('Failed to obtain container registry')
        return False
    cr = r.json()['cr']
    print('Registry URL:', cr['url'])
    print('Username:', cr['username'])
    if args.show_password:
        print('Password:', cr['password'])
    return True


@needs_login
def docker_list_args(args, server, cookies):
    r = requests.get(server + '/rest/user', cookies=cookies)
    if r.status_code != 200 or 'cr' not in r.json():
        print('Failed to obtain container registry')
        return False
    cr = r.json()['cr']
    auth = HTTPBasicAuth(cr['username'], cr['password'])
    r = requests.get('https://%s/v2/_catalog' % cr['url'], auth=auth)
    repos = r.json()['repositories']
    everything = {}
    for repo in repos:
        r = requests.get('https://%s/v2/%s/tags/list' % (cr['url'], repo), auth=auth)
        if r.status_code != 200:
            continue
        try:
            info = r.json()
            everything[repo] = info.get('tags')
        except:
            pass
    for k, v in everything.items():
        print(k + ':')
        for tag in v:
            print('  ' + tag)
    return True


@needs_login
def show_args(args, server, cookies):
    endpoint = server + '/rest/job/status'
    if args.all:
        endpoint += '/all'
    elif args.id:
        endpoint += '/%d' % args.id
    r = requests.get(endpoint, cookies=cookies)
    if r.status_code == 404:
        print('No job found')
        return False
    elif r.status_code == 200:
        jobs = r.json()
        if not args.all:
            jobs = [jobs]
        for job in jobs:
            if args.verbose:
                print('ID:', job['id'])
                print('Status:', job['status'])
                if 'score' in job:
                    print('Score:', job['score'])
                print('Workers:')
                for worker in job['workers']:
                    print('- Task:', worker['task'])
                    print('  Status:', worker['state'])
                    if 'eta' in worker:
                        print('  ETA (seconds):', worker['eta'])
                    if 'progress' in worker:
                        print('  Progress (percent):', worker['progress'] * 100)
                    if 'score' in worker:
                        print('  Score:', worker['score'])
                    if 'error' in worker:
                        print('  Error:', worker['error'])
            else:
                print('%i: %s' % (job['id'], job['status']))
    else:
        print('Error %i occurred' % r.status_code)
        return False
    return True

@needs_login
def kill_args(args, server, cookies):
    if not args.yes:
        yn = input('Are you sure? [y/N] ')
        if yn.lower() not in ('y', 'yes'):
            print('Not canceled')
            return True
    r = requests.post(server + '/rest/job/kill', cookies=cookies)
    if r.status_code == 404:
        print('No job found')
        return False
    elif r.status_code // 100 == 2:
        print('Canceled')
    else:
        print('Error %i occurred' % r.status_code)
        return False
    return True


@needs_login
def restart_args(args, server, cookies):
    if not args.yes:
        yn = input('Are you sure? [y/N] ')
        if yn.lower() not in ('y', 'yes'):
            print('Not restarted')
            return True
    if args.id:
        suffix = '/%d' % args.id
    else:
        suffix = ''
    r = requests.post(server + '/rest/job/restart' + suffix, cookies=cookies)
    if r.status_code == 404:
        print('No job found')
        return False
    elif r.status_code // 100 == 2:
        print('Restarted')
    else:
        print('Error %i occurred' % r.status_code)
        return False
    return True


@needs_login
def submit_args(args, server, cookies):
    r = requests.get(server + '/rest/user', cookies=cookies)
    if r.status_code != 200 or 'cr' not in r.json():
        print('Failed to obtain container registry')
    cr = r.json()['cr']
    client = docker.APIClient()
    cr['registry'] = cr['url']
    del cr['url']
    tag = args.tag or 'agent:latest'
    try:
        client.tag(tag, cr['registry'] + '/' + tag)
    except requests.exceptions.HTTPError:
        print('Could not find local tag')
        return False
    print('Pushing container...')
    size = {}
    for line in client.push(cr['registry'] + '/' + tag, stream=True, auth_config=cr):
        for line in line.split(b'\r\n'):
            if not line:
                continue
            line = json.loads(line)
            if 'status' not in line:
                continue
            if line['status'] == 'Pushing':
                size[line['id']] = int(line['progressDetail']['current']), int(line['progressDetail']['total'])
            elif line['status'] == 'Pushed':
                size[line['id']] = size[line['id']][1], size[line['id']][1]

            current, total = 0, 0
            for c, t in size.values():
                current += c
                total += t
            if total > 0:
                print('\u001B[2K\r%i%%' % (100 * current / total), end='', flush=True)
    print('\u001B[2K\rPushed, submitting job')
    r = requests.post(server + '/rest/job/start', json={'tag': tag}, cookies=cookies)
    if r.status_code // 100 == 2:
        print('Done')
    else:
        print('Error %i occurred' % r.status_code)
        return False
    return True


def init_parsers(subparsers):
    load_config()

    parser_login = subparsers.add_parser('login', description='Log into server')
    parser_login.set_defaults(func=login_args)
    parser_login.add_argument('--email', type=str, help='Your email address')
    parser_login.add_argument('--password', type=str, help='Your password (you should use --password-stdin instead)')
    parser_login.add_argument('--password-stdin', action='store_true', help='Read password from stdin')
    parser_login.add_argument('--server', type=str, help='Server to log into')

    parser_logout = subparsers.add_parser('logout', description='Log out of server')
    parser_logout.set_defaults(func=logout_args)

    parser_leaderboard = subparsers.add_parser('leaderboard', description='Get leaderboard')
    parser_leaderboard.set_defaults(func=leaderboard_args)

    parser_docker = subparsers.add_parser('docker', description='Docker support commands')
    parser_docker.set_defaults(func=lambda args: parser_docker.print_help())
    subparsers_docker = parser_docker.add_subparsers()

    parser_docker_login = subparsers_docker.add_parser('login', description='Log into user Docker registry')
    parser_docker_login.set_defaults(func=docker_login_args)

    parser_docker_show = subparsers_docker.add_parser('show', description='Show information about user Docker registry')
    parser_docker_show.set_defaults(func=docker_show_args)
    parser_docker_show.add_argument('-p', '--show-password', action='store_true', help='Show login password')

    parser_docker_list = subparsers_docker.add_parser('list', description='List contents of Docker registry')
    parser_docker_list.set_defaults(func=docker_list_args)

    parser_job = subparsers.add_parser('job', description='Operations on jobs')
    parser_job.set_defaults(func=lambda args: parser_job.print_help())
    subparsers_job = parser_job.add_subparsers()

    parser_job_show = subparsers_job.add_parser('show', description='Show current job, if it exists')
    parser_job_show.set_defaults(func=show_args)
    parser_job_show.add_argument('id', nargs='?', type=int, help='List a specific job ID')
    parser_job_show.add_argument('-v', '--verbose', action='store_true', help='Be more verbose')
    parser_job_show.add_argument('-a', '--all', action='store_true', help='Show all jobs')

    parser_job_kill = subparsers_job.add_parser('cancel', description='Cancel current job')
    parser_job_kill.set_defaults(func=kill_args)
    parser_job_kill.add_argument('-y', '--yes', action='store_true', help='Do not display confirmation')

    parser_job_restart = subparsers_job.add_parser('restart', description='Restart job')
    parser_job_restart.set_defaults(func=restart_args)
    parser_job_restart.add_argument('-y', '--yes', action='store_true', help='Do not display confirmation')
    parser_job_restart.add_argument('id', nargs='?', type=int, help='Job ID to restart (default: latest)')

    parser_job_submit = subparsers_job.add_parser('submit', description='Submit new job')
    parser_job_submit.set_defaults(func=submit_args)
    parser_job_submit.add_argument('-t', '--tag', type=str, help='Local tag to push')


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Run OpenAI Retro Contest support code')
    parser.set_defaults(func=lambda args: parser.print_help())
    init_parsers(parser.add_subparsers())
    args = parser.parse_args(argv)
    if not args.func(args):
        sys.exit(1)


if __name__ == '__main__':
    main()
