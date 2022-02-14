import asyncio
import importlib
import importlib.resources
import inspect
import os
import pathlib
import pwd
import signal
import sys
import time
import unittest

from ...Stream import NullStream, PipeStream, ManualStream
from ...PipelineNode import PipelineProcess
from ...util import which, export, Pipe
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

        with NullStream() as null_stream:
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
            with NullStream() as null_stream:
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
class TestCreatePoll(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        test_file = cwd / 'tmp.txt'
        args = [which('touch'), test_file]
        event_loop = asyncio.new_event_loop()

        async def run_and_wait(event_loop):
            with NullStream() as null_stream:
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

            return process

        process = event_loop.run_until_complete(run_and_wait(event_loop))
                
        poll_rc = process.poll()
        poll2_rc = process.poll()

        self.assertEqual(process.proc.returncode, 0)
        self.assertEqual(poll_rc, [process.proc.returncode])
        self.assertEqual(poll2_rc, [process.proc.returncode])
        self.assertTrue(test_file.exists())

@export
@register()
class TestCreateTerminatePoll(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        args = [which('sleep'), "1"]
        event_loop = asyncio.new_event_loop()

        async def run_and_wait(event_loop):
            with NullStream() as null_stream:
                process = await PipelineProcess.create(
                    event_loop,
                    cwd = cwd.resolve(),
                    env = {},
                    args = args,
                    stdin_stream = null_stream,
                    stdout_stream = null_stream,
                    stderr_stream = null_stream
                )

            return process

        process = event_loop.run_until_complete(run_and_wait(event_loop))
        
        process.terminate()

        poll_rc = process.poll(0.1)

        self.assertEqual(process.proc.returncode, -signal.SIGTERM)
        self.assertEqual(poll_rc, [-signal.SIGTERM])

        self.assertEqual(process.wait(), [-signal.SIGTERM])

@export
@register()
class TestCreateKillPoll(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        args = [which('sleep'), "1"]
        event_loop = asyncio.new_event_loop()

        async def run_and_wait(event_loop):
            with NullStream() as null_stream:
                process = await PipelineProcess.create(
                    event_loop,
                    cwd = cwd.resolve(),
                    env = {},
                    args = args,
                    stdin_stream = null_stream,
                    stdout_stream = null_stream,
                    stderr_stream = null_stream
                )

            return process

        process = event_loop.run_until_complete(run_and_wait(event_loop))
        
        process.kill()

        poll_rc = process.poll(0.1)

        self.assertEqual(process.proc.returncode, -signal.SIGKILL)
        self.assertEqual(poll_rc, [-signal.SIGKILL])

        self.assertEqual(process.wait(), [-signal.SIGKILL])

@export
@register()
class TestCreatePollFail(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        args = [which('sleep'), "1"]
        event_loop = asyncio.new_event_loop()

        async def run_and_wait(event_loop):
            with NullStream() as null_stream:
                process = await PipelineProcess.create(
                    event_loop,
                    cwd = cwd.resolve(),
                    env = {},
                    args = args,
                    stdin_stream = null_stream,
                    stdout_stream = null_stream,
                    stderr_stream = null_stream
                )

            return process

        process = event_loop.run_until_complete(run_and_wait(event_loop))
        
        poll_rc = process.poll()

        self.assertEqual(process.proc.returncode, None)
        self.assertEqual(poll_rc, [None])

        self.assertEqual(process.wait(), [0])

@export
@register()
class TestCreateWithDifferentUser(TmpDirMixin):
    def setUp(self):
        super().setUp()

        if ((sys.version_info.major, sys.version_info.minor) < (3, 9)):
            raise unittest.SkipTest("Python version is less than 3.9")

        if os.getuid() != 0:
            raise unittest.SkipTest("Not running as root")

        def unless_key_error(fun):
            try:
                return fun()
            except KeyError:
                return None

        self.uid = unless_key_error(lambda: pwd.getpwnam('nobody').pw_uid)

        if self.uid is None:
            raise unittest.SkipTest("No user exists with name 'nobody'")

    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        args = [which('id'), '-u']
        event_loop = asyncio.new_event_loop()

        async def run_and_wait(event_loop):
            with NullStream() as null_stream, PipeStream(None) as stdout_stream:
                process = await PipelineProcess.create(
                    event_loop,
                    cwd = cwd.resolve(),
                    env = {},
                    args = args,
                    stdin_stream = null_stream,
                    stdout_stream = stdout_stream,
                    stderr_stream = null_stream,
                    user = 'nobody'
                )
                stdout_stream.close_writer()

                await process.wait_async()
                return stdout_stream.reader().read()

        observed_uid = event_loop.run_until_complete(run_and_wait(event_loop))
        self.assertEqual(observed_uid.strip(), str(self.uid))

@export
@register()
class TestCreateWithDifferentGroup(TmpDirMixin):
    def setUp(self):
        super().setUp()

        if ((sys.version_info.major, sys.version_info.minor) < (3, 9)):
            raise unittest.SkipTest("Python version is less than 3.9")

        if os.getuid() != 0:
            raise unittest.SkipTest("Not running as root")

        def unless_key_error(fun):
            try:
                return fun()
            except KeyError:
                return None

        self.gid = unless_key_error(lambda: pwd.getpwnam('nobody').pw_gid)

        if self.gid is None:
            raise unittest.SkipTest("No group exists with name 'nobody'")

    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        args = [which('id'), '-g']
        event_loop = asyncio.new_event_loop()

        async def run_and_wait(event_loop):
            with NullStream() as null_stream, PipeStream(None) as stdout_stream:
                process = await PipelineProcess.create(
                    event_loop,
                    cwd = cwd.resolve(),
                    env = {},
                    args = args,
                    stdin_stream = null_stream,
                    stdout_stream = stdout_stream,
                    stderr_stream = null_stream,
                    group = self.gid
                )
                stdout_stream.close_writer()

                await process.wait_async()
                return stdout_stream.reader().read()

        observed_gid = event_loop.run_until_complete(run_and_wait(event_loop))
        self.assertEqual(observed_gid.strip(), str(self.gid))
        

@export
@register()
class TestCreateWait(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        test_file = cwd / 'tmp.txt'
        args = [which('touch'), test_file]
        event_loop = asyncio.new_event_loop()

        async def run_and_wait(event_loop):
            with NullStream() as null_stream:
                process = await PipelineProcess.create(
                    event_loop,
                    cwd = cwd.resolve(),
                    env = {},
                    args = args,
                    stdin_stream = null_stream,
                    stdout_stream = null_stream,
                    stderr_stream = null_stream
                )

            return process

        process = event_loop.run_until_complete(run_and_wait(event_loop))
                
        wait_rc = process.wait()

        self.assertEqual(process.proc.returncode, 0)
        self.assertEqual(wait_rc, [process.proc.returncode])
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
                with Pipe() as pipe:
                    with NullStream() as null_stream, ManualStream(fileobj_w=pipe.writer) as stdout_stream:
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
                        pipe.close_writer()
                        observed = pipe.read()

                await process.wait_async()

                return process, observed

            process, observed = event_loop.run_until_complete(run_and_wait())

            self.assertEqual(process.proc.returncode, 0)
            self.assertEqual(message, observed)
