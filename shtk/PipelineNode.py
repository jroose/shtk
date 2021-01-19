import abc
import subprocess
import asyncio
import contextlib
import time

from .util import *

__all__ = []

@export
class PipelineNode(abc.ABC):
    def __init__(self, job):
        self.children = []

    @classmethod
    async def create(cls, *args, **kwargs):
        instance = cls(*args, **kwargs)
        await instance.run()
        return instance

    async def run(self):
        pass

    @abc.abstractmethod
    def __repr__(self):
        pass

    @abc.abstractmethod
    def __str__(self):
        pass

#@export
#class PipelineOr(PipelineNode):
#    def __init__(self, job, child_factories, stdin_stream, stdout_stream, stderr_stream):
#        super().__init__(job)
#        self.child_factories = child_factories
#        self.stdin_stream = stdin_stream
#        self.stdout_stream = stdout_stream
#        self.stderr_stream = stderr_stream
#        self.lock = threading.Lock()
#
#        self.thread = threading.Thread(
#            target = self.worker
#        )
#        self.thread.start()
#
#    def worker(self):
#        with self.lock:
#            assert len(self.child_factories) > 0
#            for child in self.child_factories:
#                ret = child.build(
#                    job=job,
#                    stdin_stream=self.stdin_stream,
#                    stdout_stream=self.stdout_stream,
#                    stderr_stream=self.stderr_stream
#                )
#                self.children.append(ret)
#                child_result = ret.wait()
#                success = all(rc == 0 for rc in child_result)
#                if success:
#                    break
#
#    def wait(self):
#        self.thread.wait()
#        with self.lock:
#            return self.children[-1].wait()

@export
class PipelineChannel(PipelineNode):
    def __init__(self, job, left, right):
        super().__init__(job)

        self.left = left
        self.right = right

        self.children.extend((self.left, self.right))

    def __repr__(self):
        return f"{repr(self.left)} | {repr(self.right)}"

    def __str__(self):
        return f"{str(self.left)} | {str(self.right)}"

    async def wait(self):
        ret = []
        ret.extend(await self.left.wait())
        ret.extend(await self.right.wait())
        return ret

@export
class PipelineProcess(PipelineNode):
    def __init__(self, job, args, env, stdin_stream, stdout_stream, stderr_stream):
        super().__init__(job)
        self.args = args
        self.env = env
        self.proc = None
        self.cwd = job.shell.current_working_directory

        self.stdin_stream = stdin_stream
        self.stdout_stream = stdout_stream
        self.stderr_stream = stderr_stream

        self.stdin = self.stdin_stream.reader()
        self.stdout = self.stdout_stream.writer()
        self.stderr = self.stderr_stream.writer()

        assert len(self.args) > 0

    async def run(self):
        self.proc = await asyncio.create_subprocess_exec(
            *self.args,
            stdin = self.stdin,
            stdout = self.stdout,
            stderr = self.stderr,
            cwd = self.cwd,
            env = self.env,
            restore_signals = True,
            close_fds = True
        )

    def __repr__(self):
        return f"PipelineProcess(job={self.job}, args={repr(self.args)}, env={repr(self.env)}, stdin_stream={self.stdin_stream}, stdout_stream={self.stdout_stream}, stderr_stream={self.stderr_stream})"

    def __str__(self):
        return f"PipelineProcess(args={repr(self.args)})"

    async def wait(self):
        return [await self.proc.wait()]
