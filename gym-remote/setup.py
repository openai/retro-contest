from setuptools import setup
import sys
import os
import shutil

VERSION_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'VERSION')

if not os.path.exists(os.path.join(os.path.dirname(__file__), '.git')):
    use_scm_version = False
    shutil.copy('VERSION', 'gym_remote/VERSION.txt')
else:
    def version_scheme(version):
        with open(VERSION_PATH) as v:
            version_file = v.read()
        if version.distance:
            version_file += '.dev%d' % version.distance
        return version_file

    def local_scheme(version):
        v = ''
        if version.distance:
            v = '+' + version.node
        return v
    use_scm_version = {'write_to': 'retro/VERSION.txt',
                       'version_scheme': version_scheme,
                       'local_scheme': local_scheme}


setup(
    name='gym-remote',
    version=open(VERSION_PATH, 'r').read(),
    license='MIT',
    install_requires=[
        'gym',
    ],
    packages=['gym_remote'],
    setup_requires=['pytest-runner'],
    use_scm_version=use_scm_version
)
