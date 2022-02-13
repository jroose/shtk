import asyncio
import contextlib
import os
import pathlib
import signal
import sys
import time
import unittest

from ...Stream import Stream, NullStream, FileStream, PipeStream
from ...PipelineNode import PipelineProcess, PipelineChannel
from ...util import which, export

from ..test_util import register, TmpDirMixin

__all__ = []

@export
@register()
class TestCreateAndWait(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        cat = which('cat')
        message = "Hello World!"
        event_loop = asyncio.new_event_loop()

        async def run_and_wait():
            with PipeStream(None) as p3, NullStream() as null_stream:
                with PipeStream(None) as p1, PipeStream(None) as p2:
                    cat1 = await PipelineProcess.create(
                        event_loop,
                        cwd = cwd.resolve(),
                        env = {},
                        args = [cat],
                        stdin_stream = p1,
                        stdout_stream = p2,
                        stderr_stream = null_stream
                    )

                    cat2 = await PipelineProcess.create(
                        event_loop,
                        cwd = cwd.resolve(),
                        env = {},
                        args = [cat],
                        stdin_stream = p2,
                        stdout_stream = p3,
                        stderr_stream = null_stream
                    )

                    channel = await PipelineChannel.create(
                        event_loop,
                        left = cat1,
                        right = cat2
                    )

                    p1.writer().write(message)

                p3.close_writer()

                stdout_result = p3.reader().read()

                returncodes = await channel.wait_async()

            return channel, returncodes, stdout_result

        channel, returncodes, stdout_result = event_loop.run_until_complete(run_and_wait())

        processes = [
            channel.left.proc,
            channel.right.proc
        ]

        self.assertEqual([rc for rc in returncodes], [0, 0])
        self.assertEqual([p.returncode for p in processes], [0, 0])
        self.assertEqual(stdout_result, message)

@export
@register()
class TestTerminate(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        cat = which('cat')
        sleep = which('sleep')
        event_loop = asyncio.new_event_loop()

        async def run_and_wait():
            with NullStream() as null_stream, PipeStream(None) as p2:
                sleep1 = await PipelineProcess.create(
                    event_loop,
                    cwd = cwd.resolve(),
                    env = {},
                    args = [sleep, "1"],
                    stdin_stream = null_stream,
                    stdout_stream = p2,
                    stderr_stream = null_stream
                )

                cat2 = await PipelineProcess.create(
                    event_loop,
                    cwd = cwd.resolve(),
                    env = {},
                    args = [cat],
                    stdin_stream = p2,
                    stdout_stream = null_stream,
                    stderr_stream = null_stream
                )

                channel = await PipelineChannel.create(
                    event_loop,
                    left = sleep1,
                    right = cat2
                )

            return channel

        channel = event_loop.run_until_complete(run_and_wait())
        channel.terminate()
        returncodes = channel.wait()

        processes = [
            channel.left.proc,
            channel.right.proc
        ]

        EXPRC = -signal.SIGTERM
        self.assertEqual([rc for rc in returncodes], [EXPRC, EXPRC])
        self.assertEqual([p.returncode for p in processes], [EXPRC, EXPRC])

@export
@register()
class TestKill(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        cat = which('cat')
        sleep = which('sleep')
        event_loop = asyncio.new_event_loop()

        async def run_and_wait():
            with NullStream() as null_stream, PipeStream(None) as p2:
                sleep1 = await PipelineProcess.create(
                    event_loop,
                    cwd = cwd.resolve(),
                    env = {},
                    args = [sleep, "1"],
                    stdin_stream = null_stream,
                    stdout_stream = p2,
                    stderr_stream = null_stream
                )

                cat2 = await PipelineProcess.create(
                    event_loop,
                    cwd = cwd.resolve(),
                    env = {},
                    args = [cat],
                    stdin_stream = p2,
                    stdout_stream = null_stream,
                    stderr_stream = null_stream
                )

                channel = await PipelineChannel.create(
                    event_loop,
                    left = sleep1,
                    right = cat2
                )

            return channel

        channel = event_loop.run_until_complete(run_and_wait())
        channel.kill()
        returncodes = channel.wait()

        processes = [
            channel.left.proc,
            channel.right.proc
        ]

        EXPRC = -signal.SIGKILL
        self.assertEqual([rc for rc in returncodes], [EXPRC, EXPRC])
        self.assertEqual([p.returncode for p in processes], [EXPRC, EXPRC])

@export
@register()
class TestKillPartial(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        test_file = 'tmp.txt'
        cat = which('cat')
        sleep = which('sleep')
        touch = which('touch')
        event_loop = asyncio.new_event_loop()

        async def run_and_wait():
            with NullStream() as null_stream, PipeStream(None) as p2:
                sleep1 = await PipelineProcess.create(
                    event_loop,
                    cwd = cwd.resolve(),
                    env = {},
                    args = [sleep, "1"],
                    stdin_stream = null_stream,
                    stdout_stream = p2,
                    stderr_stream = null_stream
                )

                touch2 = await PipelineProcess.create(
                    event_loop,
                    cwd = cwd.resolve(),
                    env = {},
                    args = [touch, test_file],
                    stdin_stream = p2,
                    stdout_stream = null_stream,
                    stderr_stream = null_stream
                )

                channel = await PipelineChannel.create(
                    event_loop,
                    left = sleep1,
                    right = touch2
                )

            time.sleep(0.1)

            return channel

        channel = event_loop.run_until_complete(run_and_wait())
        channel.kill()
        returncodes = channel.wait()

        processes = [
            channel.left.proc,
            channel.right.proc
        ]

        EXPRC = -signal.SIGKILL
        self.assertEqual([rc for rc in returncodes], [EXPRC, 0])
        self.assertEqual([p.returncode for p in processes], [EXPRC, 0])
