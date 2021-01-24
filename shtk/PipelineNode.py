import abc
import subprocess
import asyncio
import contextlib
import time

from .util import *

__all__ = []

@export
class PipelineNode(abc.ABC):
    def __init__(self):
        self.children = []
        self.stdin_stream = None
        self.stderr_stream = None
        self.stdout_stream = None

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

@export
class PipelineChannel(PipelineNode):
    def __init__(self, left, right):
        super().__init__()

        self.left = left
        self.right = right

        self.stdin_stream = self.left.stdin_stream
        self.stdout_stream = self.right.stdout_stream
        self.stderr_stream = self.right.stderr_stream

        self.children.extend((self.left, self.right))

    def __repr__(self):
        return f"{self.left!r} | {self.right!r}"

    def __str__(self):
        return f"{self.left!s} | {self.right!s}"

    async def wait(self):
        ret = []
        ret.extend(await self.left.wait())
        ret.extend(await self.right.wait())
        return ret

@export
class PipelineProcess(PipelineNode):
    def __init__(self, cwd, args, env, stdin_stream, stdout_stream, stderr_stream):
        super().__init__()

        self.cwd = cwd
        self.args = args
        self.env = env
        self.proc = None

        self.stdin_stream = stdin_stream
        self.stdout_stream = stdout_stream
        self.stderr_stream = stderr_stream

        assert len(self.args) > 0

    async def run(self):
        self.proc = await asyncio.create_subprocess_exec(
            *self.args,
            stdin = self.stdin_stream.reader(),
            stdout = self.stdout_stream.writer(),
            stderr = self.stderr_stream.writer(),
            cwd = self.cwd,
            env = self.env,
            restore_signals = True,
            close_fds = True
        )

    def __repr__(self):
        return f"PipelineProcess(cwd={self.cwd!r}, args={self.args!r}, env={self.env!r}, stdin_stream={self.stdin_stream!r}, stdout_stream={self.stdout_stream!r}, stderr_stream={self.stderr_stream!r})"

    def __str__(self):
        return f"PipelineProcess(args={self.args!r})"

    async def wait(self):
        return [await self.proc.wait()]
