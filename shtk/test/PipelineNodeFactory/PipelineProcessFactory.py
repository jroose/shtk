import asyncio
import os
import pathlib
import sys
import unittest

from ...Stream import NullStream, FileStream
from ...StreamFactory import NullStreamFactory, FileStreamFactory
from ...PipelineNodeFactory import PipelineProcessFactory
from ...util import which, export
from ...Job import Job

from ..test_util import register, TmpDirMixin

__all__ = []

async def build_and_wait(factory, *args, **kwargs):
    obj = await factory.build(*args, **kwargs)
    return await obj.wait_async()

@export
@register()
class TestBuild(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        tmp_file = cwd / "tmp.txt"

        null_stream = NullStream()

        ppf = PipelineProcessFactory(which('touch'), cwd='./')
        ppf = ppf(tmp_file.resolve())
        job = Job(None, cwd=cwd)

        return_codes = job.event_loop.run_until_complete(build_and_wait(
            ppf,
            job,
            stdin_stream=null_stream,
            stdout_stream=null_stream,
            stderr_stream=null_stream
        ))

        self.assertEqual(return_codes, [0])
        self.assertTrue(tmp_file.exists())

@export
@register()
class TestBuildWithExplicitStreamsStdinStdout(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = cwd / "input.txt"
        output_file = cwd / "output.txt"
        message = "Hello World!"

        with open(input_file.resolve(), 'w') as fout:
            fout.write(message)

        stdin_stream = FileStream(input_file.resolve(), 'r')
        stdout_stream = FileStream(output_file.resolve(), 'w')
        null_stream = NullStream()

        ppf = PipelineProcessFactory(which('cat'), cwd='./')
        job = Job(None, cwd=cwd)

        return_codes = job.event_loop.run_until_complete(build_and_wait(
            ppf,
            job,
            stdin_stream=stdin_stream,
            stdout_stream=stdout_stream,
            stderr_stream=null_stream
        ))

        self.assertEqual(return_codes, [0])

        self.assertTrue(output_file.exists())
        with open(output_file.resolve(), 'r') as fin:
            observed = fin.read()

        self.assertEqual(message, observed)

@export
@register()
class TestBuildWithExplicitStreamsStderr(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = cwd / "input.txt"
        output_file = cwd / "output.txt"

        stderr_stream = FileStream(output_file.resolve(), 'w')
        null_stream = NullStream()

        ppf = PipelineProcessFactory(which('cat'), input_file.resolve(), cwd='./')
        job = Job(None, cwd=cwd)

        return_codes = job.event_loop.run_until_complete(build_and_wait(
            ppf,
            job,
            stdin_stream=null_stream,
            stdout_stream=null_stream,
            stderr_stream=stderr_stream
        ))

        self.assertEqual(return_codes, [1])

        with open(output_file.resolve(), 'r') as fin:
            observed = fin.read()

        self.assertTrue('No such file or directory' in observed)

@export
@register()
class TestBuildWithStreamFactoryStdinStdout(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = cwd / "input.txt"
        output_file = cwd / "output.txt"
        message = "Hello World!"

        with open(input_file.resolve(), 'w') as fout:
            fout.write(message)

        stdin_stream = FileStreamFactory(input_file.resolve(), 'r')
        stdout_stream = FileStreamFactory(output_file.resolve(), 'w')
        null_stream = None

        ppf = PipelineProcessFactory(which('cat'), cwd='./')
        job = Job(ppf, cwd=cwd)

        return_codes = job.event_loop.run_until_complete(build_and_wait(
            ppf.stdin(stdin_stream).stdout(stdout_stream).stderr(null_stream),
            job
        ))

        self.assertEqual(return_codes, [0])

        self.assertTrue(output_file.exists())
        with open(output_file.resolve(), 'r') as fin:
            observed = fin.read()

        self.assertEqual(message, observed)

@export
@register()
class TestBuildWithStreamFactoryStderr(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = cwd / "input.txt"
        output_file = cwd / "output.txt"

        stderr_stream = FileStreamFactory(output_file.resolve(), 'w')
        null_stream = None

        ppf = PipelineProcessFactory(which('cat'), input_file.resolve(), cwd='./')
        job = Job(ppf, cwd=cwd)

        return_codes = job.event_loop.run_until_complete(build_and_wait(
            ppf.stdin(null_stream).stdout(null_stream).stderr(stderr_stream),
            job
        ))

        self.assertEqual(return_codes, [1])

        with open(output_file.resolve(), 'r') as fin:
            observed = fin.read()

        self.assertTrue('No such file or directory' in observed)

@export
@register()
class TestBuildWithFilePathStdinStdout(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = cwd / "input.txt"
        output_file = cwd / "output.txt"
        message = "Hello World!"

        with open(input_file.resolve(), 'w') as fout:
            fout.write(message)

        stdin = str(input_file.resolve())
        stdout = str(output_file.resolve())
        null = None

        ppf = PipelineProcessFactory(which('cat'), cwd='./')
        job = Job(ppf, cwd=cwd)

        return_codes = job.event_loop.run_until_complete(build_and_wait(
            ppf.stdin(stdin).stdout(stdout).stderr(null),
            job
        ))

        self.assertEqual(return_codes, [0])

        self.assertTrue(output_file.exists())
        with open(output_file.resolve(), 'r') as fin:
            observed = fin.read()

        self.assertEqual(message, observed)

@export
@register()
class TestBuildWithFilePathStderr(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = cwd / "input.txt"
        output_file = cwd / "output.txt"

        stderr = str(output_file.resolve())
        null = None

        ppf = PipelineProcessFactory(which('cat'), input_file.resolve(), cwd='./')
        job = Job(ppf, cwd=cwd)

        return_codes = job.event_loop.run_until_complete(build_and_wait(
            ppf.stdin(null).stdout(null).stderr(stderr),
            job
        ))

        self.assertEqual(return_codes, [1])

        with open(output_file.resolve(), 'r') as fin:
            observed = fin.read()

        self.assertTrue('No such file or directory' in observed)

@export
@register()
class TestBuildWithPathlibStdinStdout(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = cwd / "input.txt"
        output_file = cwd / "output.txt"
        message = "Hello World!"

        with open(input_file.resolve(), 'w') as fout:
            fout.write(message)

        stdin = input_file.resolve()
        stdout = output_file.resolve()
        null = None

        ppf = PipelineProcessFactory(which('cat'), cwd='./')
        job = Job(ppf, cwd=cwd)

        return_codes = job.event_loop.run_until_complete(build_and_wait(
            ppf.stdin(stdin).stdout(stdout).stderr(null),
            job
        ))

        self.assertEqual(return_codes, [0])

        self.assertTrue(output_file.exists())
        with open(output_file.resolve(), 'r') as fin:
            observed = fin.read()

        self.assertEqual(message, observed)

@export
@register()
class TestBuildWithPathlibStderr(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = cwd / "input.txt"
        output_file = cwd / "output.txt"

        stderr = output_file.resolve()
        null = None

        ppf = PipelineProcessFactory(which('cat'), input_file.resolve(), cwd='./')
        job = Job(ppf, cwd=cwd)

        return_codes = job.event_loop.run_until_complete(build_and_wait(
            ppf.stdin(null).stdout(null).stderr(stderr),
            job
        ))

        self.assertEqual(return_codes, [1])

        with open(output_file.resolve(), 'r') as fin:
            observed = fin.read()

        self.assertTrue('No such file or directory' in observed)
