import asyncio
import importlib
import importlib.resources
import inspect
import os
import pathlib
import sys
import time
import unittest

from ...Stream import NullStream, PipeStream
from ...PipelineNode import PipelineProcess
from ...util import which, export
from ...Job import Job

from ..test_util import register, TmpDirMixin

__all__ = []

@export
@register()
class TestConstruct(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name).resolve()
        args = [which('touch'), "tmp.txt"]
        event_loop = asyncio.new_event_loop()

        with NullStream(None) as null_stream:
            process = PipelineProcess(
                event_loop,
                cwd = cwd,
                env = {},
                args = args,
                stdin_stream = null_stream,
                stdout_stream = null_stream,
                stderr_stream = null_stream
            )

        self.assertEqual(process.cwd, cwd)
        self.assertEqual(process.args, args)

        str(process)
        repr(process)

@export
@register()
class TestCreateAndWaitAsync(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        test_file = cwd / 'tmp.txt'
        args = [which('touch'), test_file]
        event_loop = asyncio.new_event_loop()

        async def run_and_wait():
            with NullStream(None) as null_stream:
                process = await PipelineProcess.create(
                    event_loop,
                    cwd = cwd.resolve(),
                    env = {},
                    args = args,
                    stdin_stream = null_stream,
                    stdout_stream = null_stream,
                    stderr_stream = null_stream
                )

            await process.wait_async()

            return process

        process = event_loop.run_until_complete(run_and_wait())

        self.assertEqual(process.proc.returncode, 0)
        self.assertTrue(test_file.exists())

@export
@register()
class TestCreatePollWait(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        test_file = cwd / 'tmp.txt'
        args = [which('touch'), test_file]
        event_loop = asyncio.new_event_loop()

        async def run_and_wait():
            with NullStream(None) as null_stream:
                process = await PipelineProcess.create(
                    event_loop,
                    cwd = cwd.resolve(),
                    env = {},
                    args = args,
                    stdin_stream = null_stream,
                    stdout_stream = null_stream,
                    stderr_stream = null_stream
                )

                time.sleep(0.1)
                poll_rc = process.poll()

                wait_rc = await process.wait_async()

            return poll_rc, wait_rc, process

        poll_rc, wait_rc, process = event_loop.run_until_complete(run_and_wait())

        self.assertEqual(poll_rc, process.proc.returncode)
        self.assertEqual(wait_rc, process.proc.returncode)
        self.assertEqual(process.proc.returncode, 0)
        self.assertTrue(test_file.exists())

@export
@register()
class TestEnvironmentVariableExists(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        from .. import test_util
        with importlib.resources.path(test_util.__package__, 'echo_env.py') as echo_env:
            args = [which('python3'), echo_env]
            message = 'Hello World!'
            event_loop = asyncio.new_event_loop()

            async def run_and_wait():
                with NullStream(None) as null_stream, PipeStream(None) as stdout_stream:
                    process = await PipelineProcess.create(
                        event_loop,
                        cwd = cwd.resolve(),
                        env = {
                            'A': 'wrong output',
                            'MESSAGE': message,
                            'Z': 'wrong output'
                        },
                        args = [which('python3'), echo_env, "MESSAGE"],
                        stdin_stream = null_stream,
                        stdout_stream = stdout_stream,
                        stderr_stream = null_stream
                    )
                    stdout_stream.close_writer()
                    observed = stdout_stream.reader().read()
                    stdout_stream.close()

                await process.wait_async()

                return process, observed

            process, observed = event_loop.run_until_complete(run_and_wait())

            self.assertEqual(process.proc.returncode, 0)
            self.assertEqual(message, observed)
