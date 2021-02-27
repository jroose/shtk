import asyncio
import os
import pathlib
import signal
import sys
import time
import unittest

from ...Job import Job, NonzeroExitCodeException
from ...Stream import NullStream, FileStream
from ...StreamFactory import NullStreamFactory, FileStreamFactory, PipeStreamFactory
from ...PipelineNodeFactory import PipelineProcessFactory, PipelineChannelFactory
from ...util import which, export

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

        job = Job(cat)
        job.run(
            stdin_factory = PipeStreamFactory(),
            stdout_factory = PipeStreamFactory(),
            stderr_factory = NullStreamFactory()
        )

        job.stdin.write(message)
        job.stdin.close()
        observed = job.stdout.read()
        job.stdout.close()

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

        job = Job(cat(input_file))

        self.assertIsNone(job.stdin)
        self.assertIsNone(job.stdout)
        self.assertIsNone(job.stderr)

        job.run(
            stdin_factory = NullStreamFactory(),
            stdout_factory = NullStreamFactory(),
            stderr_factory = PipeStreamFactory()
        )

        observed = job.stderr.read()
        job.stdout.close()

        return_codes = job.wait(exceptions=False)

        self.assertEqual(return_codes, (1,))
        self.assertTrue('No such file or directory' in observed)

@export
@register()
class TestBuildWithNonexistentFileWithException(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = cwd / "non\\existent"

        cat = PipelineProcessFactory(which('cat'))

        job = Job(cat(input_file))

        self.assertIsNone(job.stdin)
        self.assertIsNone(job.stdout)
        self.assertIsNone(job.stderr)

        job.run(
            stdin_factory = NullStreamFactory(),
            stdout_factory = NullStreamFactory(),
            stderr_factory = PipeStreamFactory()
        )

        observed = job.stderr.read()
        job.stdout.close()

        self.assertTrue('No such file or directory' in observed)

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
