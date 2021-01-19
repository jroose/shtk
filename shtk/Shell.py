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
            self.current_working_directory = pathlib.Path(cwd)
            self.previous_working_directory = None

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
                command_path = (self.current_working_directory / path).resolve()
        else:
            command_path = which(name)

        if command_path is None:
            raise RuntimeError(f"{name}: command not found")
                
        if user is None:
            return PipelineProcessFactory(command_path)
        else:
            return PipelineProcessFactory('sudo', '-u', user, command_path)

    def cd(self, path):
        with self.lock:
            path = pathlib.Path(path)
            if not path.is_absolute():
                new_cwd = (self.current_working_directory / path).resolve()
            else:
                new_cwd = path.resolve()

            self.previous_working_directory = self.current_working_directory
            self.current_working_directory = new_cwd.resolve()

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

    @contextlib.contextmanager
    def get_stdin(self):
        yield self.stdin

    @contextlib.contextmanager
    def get_stdout(self):
        yield self.stdout

    @contextlib.contextmanager
    def get_stderr(self):
        yield self.stderr

    def __enter__(self):
        tvars = self._get_thread_vars()
        tvars.setdefault('shell_stack', [])
        tvars['shell_stack'].append(self)

        self.event_loop = asyncio.new_event_loop()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.event_loop.run_until_complete(
            self.event_loop.shutdown_asyncgens()
        )
        self.event_loop.close()

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
                        job.run()    
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
            job = Job(self, pipeline_factory)
            self.event_loop.run_until_complete(
                run_and_wait(job, exceptions=exceptions, wait=wait)
            )
            ret.append(job)

        return ret

    def evaluate(self, pipeline_factory, exceptions=None):
        async def run_and_wait(job, exceptions=None):
            await job.run()
            ret = job.stdout_stream.reader().read() # This will deadlock if an async job or process fails to close the writer
            await job.wait_async(exceptions=exceptions)
            return ret


        if exceptions is None:
            exceptions = self.exceptions

        job = Job(self, pipeline_factory, stdout_factory=PipeStreamFactory())
        
        ret = asyncio.run(run_and_wait(job, exceptions=exceptions))

        return ret

default_shell = Shell()
default_shell.__enter__()
atexit.register(default_shell.__exit__, None, None, None)
