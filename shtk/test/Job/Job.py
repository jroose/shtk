import asyncio
import os
import pathlib
import signal
import sys
import time
import unittest

from ...Job import Job, NonzeroExitCodeException
from ...Stream import NullStream, FileStream
from ...StreamFactory import NullStreamFactory, FileStreamFactory, PipeStreamFactory, ManualStreamFactory
from ...PipelineNodeFactory import PipelineProcessFactory, PipelineChannelFactory
from ...util import which, export, Pipe

from ..test_util import register, TmpDirMixin

__all__ = []

@export
@register()
class TestWait(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = cwd / "input.txt"
        output_file = cwd / "output.txt"
        message = "Hello World!"

        with open(input_file.resolve(), 'w') as fout:
            fout.write(message)

        stdin_factory = FileStreamFactory(input_file, 'r')
        stdout_factory = FileStreamFactory(output_file, 'w')
        null_factory = NullStreamFactory()

        cat1 = PipelineProcessFactory(which('cat')).stdin(stdin_factory)
        cat2 = PipelineProcessFactory(which('cat')).stdout(stdout_factory)
        false = PipelineProcessFactory(which('false'))

        job = Job(cat1 | cat2 | false)
        job.run(
            stdin_factory = null_factory,
            stdout_factory = null_factory,
            stderr_factory = null_factory
        )

        self.assertEqual(job.wait(job.pipeline.left.left, exceptions=False), (0,))
        self.assertEqual(job.wait(job.pipeline.left.right, exceptions=False), (0,))
        self.assertEqual(job.wait(job.pipeline.right, exceptions=False), (1,))

        self.assertTrue(output_file.exists())

        with open(output_file.resolve(), 'r') as fin:
            observed = fin.read()

        self.assertEqual(message, observed)

@export
@register()
class TestBuildWithFileStdinStdout(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = cwd / "input.txt"
        output_file = cwd / "output.txt"
        message = "Hello World!"

        with open(input_file.resolve(), 'w') as fout:
            fout.write(message)

        stdin_factory = FileStreamFactory(input_file, 'r')
        stdout_factory = FileStreamFactory(output_file, 'w')
        null_factory = NullStreamFactory()


        cat = PipelineProcessFactory(which('cat'))

        job = Job(cat)

        job.run(
            stdin_factory = stdin_factory,
            stdout_factory = stdout_factory,
            stderr_factory = null_factory
        )

        return_codes = job.wait()

        self.assertEqual(return_codes, (0,))

        self.assertTrue(output_file.exists())
        with open(output_file.resolve(), 'r') as fin:
            observed = fin.read()

        self.assertEqual(message, observed)

@export
@register()
class TestBuildWithPipeStdinStdout(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = cwd / "input.txt"
        output_file = cwd / "output.txt"
        message = "Hello World!"

        cat = PipelineProcessFactory(which('cat'))

        with Pipe() as stdout_pipe:
            with Pipe() as stdin_pipe:
                job = Job(cat)
                job.run(
                    stdin_factory = ManualStreamFactory(fileobj_r=stdin_pipe.reader),
                    stdout_factory = ManualStreamFactory(fileobj_w=stdout_pipe.writer),
                    stderr_factory = NullStreamFactory()
                )

                stdin_pipe.write(message)

            stdout_pipe.close_writer()

            observed = stdout_pipe.read()

            return_codes = job.wait()

        self.assertEqual(return_codes, (0,))

        self.assertEqual(message, observed)

@export
@register()
class TestBuildWithNonexistentFileNoException(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = cwd / "input.txt"

        cat = PipelineProcessFactory(which('cat'))

        with Pipe() as stderr_pipe:
            job = Job(cat(input_file))

            self.assertIsNone(job.stdin)
            self.assertIsNone(job.stdout)
            self.assertIsNone(job.stderr)

            job.run(
                stdin_factory = NullStreamFactory(),
                stdout_factory = NullStreamFactory(),
                stderr_factory = ManualStreamFactory(fileobj_w=stderr_pipe.writer)
            )

            stderr_pipe.close_writer()

            return_codes = job.wait(exceptions=False)

            observed = stderr_pipe.read()

        self.assertEqual(return_codes, (1,))
        self.assertIn('No such file or directory', observed)

@export
@register()
class TestBuildWithNonexistentFileWithException(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = cwd / "non\\existent"

        cat = PipelineProcessFactory(which('cat'))

        with Pipe() as stderr_pipe:
            job = Job(cat(input_file))

            self.assertIsNone(job.stdin)
            self.assertIsNone(job.stdout)
            self.assertIsNone(job.stderr)

            job.run(
                stdin_factory = NullStreamFactory(),
                stdout_factory = NullStreamFactory(),
                stderr_factory = ManualStreamFactory(fileobj_w=stderr_pipe.writer)
            )

            stderr_pipe.close_writer()

            observed = stderr_pipe.read()

        self.assertIn('No such file or directory', observed)

        with self.assertRaises(NonzeroExitCodeException):
            job.wait()

@export
@register()
class TestJobTerminate(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)

        job = Job(
            PipelineChannelFactory(
                PipelineProcessFactory(
                    which('sleep')
                )('1'),
                PipelineProcessFactory(
                    which('sleep')
                )('10')
            )
        )

        job.run(
            stdin_factory = NullStreamFactory(),
            stdout_factory = NullStreamFactory(),
            stderr_factory = NullStreamFactory()
        )

        time.sleep(1.1)

        job.terminate()

        return_codes = job.wait(exceptions=False)

        self.assertEqual(return_codes, (0, -signal.SIGTERM))

@export
@register()
class TestJobKill(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)

        job = Job(
            PipelineChannelFactory(
                PipelineProcessFactory(
                    which('sleep')
                )('1'),
                PipelineProcessFactory(
                    which('sleep')
                )('10')
            )
        )

        job.run(
            stdin_factory = NullStreamFactory(),
            stdout_factory = NullStreamFactory(),
            stderr_factory = NullStreamFactory()
        )

        time.sleep(1.1)

        job.kill()

        return_codes = job.wait(exceptions=False)

        self.assertEqual(return_codes, (0, -signal.SIGKILL))
