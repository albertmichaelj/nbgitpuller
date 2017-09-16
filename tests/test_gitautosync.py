import os
import shutil
import subprocess as sp
import time
import random
import string
import pytest
from nbgitpuller import GitPuller
from nbgitpuller.pull import execute_cmd

class Remote:
    def __init__(self, path='remote'):
        self.path = path

    def __enter__(self):
        os.mkdir(self.path)
        self.git('init', '--bare')
        return self

    def __exit__(self, *args):
        shutil.rmtree(self.path)

    def git(self, *args):
        return sp.check_output(
            ['git'] + list(args),
            cwd=self.path,
            stderr=sp.STDOUT
        ).decode().strip()

class Pusher:
    def __init__(self, remote, path='pusher'):
        self.path = path
        self.remote = remote

    def __enter__(self):
        sp.check_output(['git', 'clone', self.remote.path, self.path])
        return self

    def __exit__(self, *args):
        shutil.rmtree(self.path)

    def git(self, *args):
        return sp.check_output(
            ['git'] + list(args),
            cwd=self.path,
            stderr=sp.STDOUT
        ).decode().strip()

    def write_file(self, path, content):
        with open(os.path.join(self.path, path), 'w') as f:
            f.write(content)

    def read_file(self, path):
        with open(os.path.join(self.path, path)) as f:
            return f.read()

    def push_file(self, path, content):
        self.write_file(path, content)
        self.git('add', path)
        self.git('commit', '-am', 'Ignore the message')
        self.git('push', 'origin', 'master')

class Puller:
    def __init__(self, remote, path='puller'):
        self.path = path
        self.gp = GitPuller(remote.path, 'master', path)

    def __enter__(self):
        for line in self.gp.pull():
            print(line)
        return self

    def __exit__(self, *args):
        shutil.rmtree(self.path)

    def git(self, *args):
        return sp.check_output(
            ['git'] + list(args),
            cwd=self.path,
            stderr=sp.STDOUT
        ).decode().strip()

    def write_file(self, path, content):
        with open(os.path.join(self.path, path), 'w') as f:
            f.write(content)

    def read_file(self, path):
        with open(os.path.join(self.path, path)) as f:
            return f.read()

# Tests to write:
# 1. Initialize puller with gitpuller, test for user config & commit presence
# 2. Push commit with pusher, pull with puller, valiate that nothing has changeed
# 3. Delete file in puller, run puller, make sure file is back
# 4. Make change in puller to file, make change in pusher to different part of file, run puller
# 5. Make change in puller to file, make change in pusher to same part of file, run puller
# 6. Make untracked file in puller, add file with same name to pusher, run puller

def test_initialize():
    with Remote() as remote, Pusher(remote) as pusher:
        pusher.push_file('README.md', '1')

        assert not os.path.exists('puller')
        with Puller(remote, 'puller') as puller:
            assert os.path.exists(os.path.join(puller.path, 'README.md'))
            assert puller.git('name-rev', '--name-only', 'HEAD') == 'master'
            assert puller.git('rev-parse', 'HEAD') == pusher.git('rev-parse', 'HEAD')

def test_simple_push_pull():
    with Remote() as remote, Pusher(remote) as pusher:
        pusher.push_file('README.md', '1')

        with Puller(remote) as puller:
            assert puller.git('rev-parse', 'HEAD') == pusher.git('rev-parse', 'HEAD')
            assert puller.read_file('README.md') == pusher.read_file('README.md') == '1'

            pusher.push_file('README.md', '2')
            for l in puller.gp.pull():
                print(puller.path + l)

            assert puller.git('rev-parse', 'HEAD') == pusher.git('rev-parse', 'HEAD')
            assert puller.read_file('README.md') == pusher.read_file('README.md') == '2'

