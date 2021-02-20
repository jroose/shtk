import asyncio
import os
import pathlib
import sys
import unittest

from ...Stream import NullStream, FileStream
from ...StreamFactory import NullStreamFactory, FileStreamFactory
from ...PipelineNodeFactory import PipelineProcessFactory
from ...Job import Job
from ...util import which, export

from ..test_util import register, TmpDirMixin

__all__ = []

async def build_and_wait(factory, *args, **kwargs):
    obj = await factory.build(*args, **kwargs)
    return await obj.wait_async()

@export
@register()
class TestBuildWithStdinStdout(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = cwd / "input.txt"
        output_file = cwd / "output.txt"
        message = "Hello World!"

        with open(input_file.resolve(), 'w') as fout:
            fout.write(message)

        null_stream = NullStreamFactory()

        ppf1 = PipelineProcessFactory(which('cat'), cwd='./')
        ppf2 = PipelineProcessFactory(which('cat'), cwd='./')

        ppf_channel = (ppf1 | ppf2).stdin(input_file.resolve()).stdout(output_file.resolve()).stderr(null_stream)
        job = Job(ppf_channel, cwd=cwd)

        return_codes = job.event_loop.run_until_complete(build_and_wait(
            ppf_channel,
            job
        ))

        self.assertEqual(return_codes, [0, 0])

        self.assertTrue(output_file.exists())
        with open(output_file.resolve(), 'r') as fin:
            observed = fin.read()

        self.assertEqual(message, observed)
