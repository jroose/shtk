import asyncio
import atexit
import collections
import contextlib
import os
import os.path
import pathlib
import subprocess
import sys
import threading

from .Job import *
from .util import export, which
from .PipelineNodeFactory import *
from .StreamFactory import *

__all__ = ["default_shell"]

@export
class Shell:
    _thread_vars = collections.defaultdict(dict)
    initial_umask = int(subprocess.check_output(['grep', 'Umask', f"/proc/{os.getpid()}/status"]).split()[-1], 8)
    
    def __init__(self, cwd=None, inherit_env=True, umask=None, stdin=None, stdout=None, stderr=None, exceptions=True):
        self.lock = threading.RLock()
        self.exceptions = exceptions
        self.event_loop = None

        with self.lock:
            if inherit_env:
                self.environment = {k:v for k,v in os.environ.items()}
            else:
                self.environment = {}

            if cwd is None:
                cwd = os.getcwd()
            self.cwd = pathlib.Path(cwd)
            self.pwd = None

            if umask is None:
                umask = self.initial_umask
            self.umask = umask
            
            if stdin is None:
                stdin = sys.stdin
            self.stdin = stdin
            
            if stdout is None:
                stdout = sys.stdout
            self.stdout = stdout

            if stderr is None:
                stderr = sys.stderr
            self.stderr = stderr

    def command(self, name, user=None):
        name = os.path.expanduser(name)

        if '/' in name:
            path = pathlib.Path(name)
            if path.is_absolute():
                command_path = path.resolve()
            else:
                command_path = (self.cwd / path).resolve()
        else:
            command_path = which(name)

        if command_path is None or not command_path.is_file():
            raise RuntimeError(f"{name}: command not found")

        if not os.access(command_path, os.R_OK):
            raise RuntimeError(f"{command_path}: is not readable")

        if not os.access(command_path, os.X_OK):
            raise RuntimeError(f"{command_path}: is not executable")
                
        if user is None:
            return PipelineProcessFactory(command_path)
        else:
            return PipelineProcessFactory('sudo', '-u', user, command_path)

    def cd(self, path):
        with self.lock:
            if path == '-':
                path = self.pwd

            path = pathlib.Path(path)
            if not path.is_absolute():
                new_cwd = (self.cwd / path).resolve()
            else:
                new_cwd = path.resolve()

            self.pwd = self.cwd
            self.cwd = new_cwd.resolve()

    @contextlib.contextmanager
    def cd_manager(self, new_wd):
        old_wd = self.cwd
        self.cd(new_wd)
        yield new_wd
        self.cd(old_wd)

    def export(self, **env):
        with self.lock:
            for key, value in env.items():
                self.environment[key] = value

    def getenv(self, name):
        return self.environment[name]

    @classmethod
    def _get_thread_vars(cls):
        thread_id = threading.get_ident()
        return cls._thread_vars[thread_id]

    @classmethod
    def get_shell(cls):
        tvars = cls._get_thread_vars()
        if len(tvars['shell_stack']) == 0:
            raise RuntimeError("No currently active shell")
        return tvars['shell_stack'][-1]

    def __enter__(self):
        tvars = self._get_thread_vars()
        tvars.setdefault('shell_stack', [])
        tvars['shell_stack'].append(self)

        if self.event_loop is not None:
            raise RuntimeError(f"{self.__class__} is not re-entrant.")

        self.event_loop = asyncio.new_event_loop()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.event_loop.run_until_complete(
            self.event_loop.shutdown_asyncgens()
        )
        self.event_loop.close()
        self.event_loop = None

        tvars = self._get_thread_vars()
        tvars['shell_stack'].pop()

    def __call__(self, *pipeline_factories, exceptions=None, wait=True):
        return self.run(*pipeline_factories, exceptions=exceptions, wait=wait)

    def run(self, *pipeline_factories, exceptions=None, wait=True):
        async def run_and_wait(*jobs, exceptions=None, wait=True):
            run_tasks = []
            for job in jobs:
                run_tasks.append(
                    self.event_loop.create_task(
                        job.run_async(
                            stdin_factory=ManualStreamFactory(fileobj_r=self.stdin),
                            stdout_factory=ManualStreamFactory(fileobj_w=self.stdout),
                            stderr_factory=ManualStreamFactory(fileobj_w=self.stderr)
                        )
                    )
                )

            for run_task in run_tasks:
                await run_task

            if wait:
                for job in jobs:
                    await job.wait_async(exceptions=exceptions)

        if exceptions is None:
            exceptions = self.exceptions

        ret = []
        for pipeline_factory in pipeline_factories:
            job = Job(pipeline_factory, env=self.environment, cwd=self.cwd, event_loop=self.event_loop)
            self.event_loop.run_until_complete(
                run_and_wait(job, exceptions=exceptions, wait=wait)
            )
            ret.append(job)

        return ret

    def evaluate(self, pipeline_factory, exceptions=None):
        if exceptions is None:
            exceptions = self.exceptions

        job = Job(
            pipeline_factory.stdout(PipeStreamFactory()),
            env=self.environment,
            cwd=self.cwd,
            event_loop=self.event_loop
        )

        job.run(
            stdin_factory=ManualStreamFactory(fileobj_r=self.stdin),
            stdout_factory=ManualStreamFactory(fileobj_w=self.stdout),
            stderr_factory=ManualStreamFactory(fileobj_w=self.stderr)
        )
        ret = job.stdout.read()
        job.wait(exceptions=exceptions)

        return ret

default_shell = Shell()
default_shell.__enter__()
atexit.register(default_shell.__exit__, None, None, None)
