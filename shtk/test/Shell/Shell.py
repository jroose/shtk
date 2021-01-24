import asyncio
import os
import pathlib
import sys
import unittest
import importlib.resources

from ...Shell import Shell
from ...util import which, export

from ..test_util import register, TmpDirMixin

__all__ = []

async def build_and_wait(factory, *args, **kwargs):
    obj = await factory.build(*args, **kwargs)
    return await obj.wait()

@export
@register()
class TestRunCommand(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = "input.txt"
        output_file = "output.txt"

        message = "Hello World!"

        with Shell(cwd=cwd) as sh:
            cat = sh.command('cat')

            with (cwd / input_file).open('w') as fout:
                fout.write(message)

            job = sh(
                cat.stdin(str(input_file)).stdout(str(output_file)).stderr(None),
                wait=False
            )[0]

            return_codes = job.wait()
            self.assertEqual(return_codes, [0])

            self.assertTrue(os.path.exists(str(cwd / output_file)))
            with (cwd / output_file).open('r') as fin:
                observed = fin.read()

            self.assertEqual(message, observed)

@export
@register()
class TestRunCommandAndWait(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = "input.txt"
        output_file = "output.txt"

        message = "Hello World!"

        with Shell(cwd=cwd) as sh:
            cat = sh.command('cat')

            with (cwd / input_file).open('w') as fout:
                fout.write(message)

            job = sh(
                cat.stdin(str(input_file)).stdout(str(output_file)).stderr(None)
            )[0]

            self.assertTrue(os.path.exists(str(cwd / output_file)))
            with (cwd / output_file).open('r') as fin:
                observed = fin.read()

            self.assertEqual(message, observed)

@export
@register()
class TestCommandDoesntExist(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)

        with Shell(cwd=cwd) as sh:
            with self.assertRaises(RuntimeError):
                sh.command('./DOES NOT EXIST')

@export
@register()
class TestCommandNotExecutable(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        tmpfile = cwd / "notreadable"

        tmpfile.touch(mode=0o600)

        with Shell(cwd=cwd) as sh:
            with self.assertRaises(RuntimeError):
                sh.command(f"./{tmpfile.name}")

@export
@register()
class TestCommandNotReadable(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        tmpfile = cwd / "notreadable"

        tmpfile.touch(mode=0o300)

        with Shell(cwd=cwd) as sh:
            with self.assertRaises(RuntimeError):
                sh.command(f"./{tmpfile.name}")

@export
@register()
class TestNoEnvironment(TmpDirMixin):
    def runTest(self):
        with Shell(inherit_env=False) as sh:
            self.assertEqual(len(sh.environment), 0)

@export
@register()
class TestWithEnvironment(TmpDirMixin):
    def runTest(self):
        num_existing = len(os.environ)
        message = 'Hello World!'
        MESSAGE = 'MESSAGE'
        os.environ[MESSAGE] = message
        with Shell() as sh:
            self.assertEqual(message, sh.getenv(MESSAGE))
            self.assertEqual(num_existing + 1, len(sh.environment))

@export
@register()
class TestChangeDirectory(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = "input.txt"
        output_file = "output.txt"

        message = "Hello World!"

        with Shell() as sh:
            cat = sh.command('cat')

            with (cwd / input_file).open('w') as fout:
                fout.write(message)

            job = sh(
                cat.stdin(str(input_file)).stdout(str(output_file)).stderr(None),
                wait=False
            )[0]

            return_codes = job.wait()
            self.assertEqual(return_codes, [0])

            self.assertTrue(os.path.exists(str(cwd / output_file)))
            with (cwd / output_file).open('r') as fin:
                observed = fin.read()

            self.assertEqual(message, observed)

@export
@register()
class TestEvaluate(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = "input.txt"
        output_file = "output.txt"

        message = "Hello World!"

        with Shell() as sh:
            cat = sh.command('cat')

            with (cwd / input_file).open('w') as fout:
                fout.write(message)

            observed = sh.evaluate(
                cat.stdin(str(input_file)).stderr(None)
            )

            self.assertEqual(message, observed)

@export
@register()
class TestEnvironmentSet(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        message = "Hello World!"

        from .. import test_util
        with importlib.resources.path(test_util.__package__, 'echo_env.py') as echo_env:
            with Shell() as sh:
                sh.export(
                    MESSAGE = message
                )

                python3 = sh.command('python3')

                observed = sh.evaluate(
                    python3(echo_env, "MESSAGE")
                )

                self.assertEqual(message, observed)

@export
@register()
class TestEnvironmentSetGet(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        message = "Hello World!"

        from .. import test_util

        with Shell() as sh:
            sh.export(
                MESSAGE = message
            )

            observed = sh.getenv('MESSAGE')

            self.assertEqual(message, observed)

@export
@register()
class TestChangeDirectoryManager(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = cwd / "input.txt"
        output_file = cwd / "output.txt"

        message = "Hello World!"

        os.chdir("/")

        with Shell() as sh:
            cat = sh.command(which('cat'))

            with input_file.open('w') as fout:
                fout.write(message)

            old_cwd = sh.cwd
            self.assertNotEqual(old_cwd, cwd)
            with sh.cd_manager(cwd) as target_cwd:
                self.assertEqual(cwd, target_cwd)
                job = sh(
                    cat.stdin(input_file.name).stdout(output_file.name).stderr(None),
                    wait=False
                )[0]
                self.assertEqual(sh.cwd, cwd)
                self.assertEqual(sh.pwd, old_cwd)
            self.assertEqual(sh.cwd, old_cwd)
            self.assertEqual(sh.pwd, cwd)

            return_codes = job.wait()
            self.assertEqual(return_codes, [0])

            self.assertTrue(os.path.exists(str(output_file)))
            with output_file.open('r') as fin:
                observed = fin.read()

            self.assertEqual(message, observed)

@export
@register()
class TestRunCommandDefaultShell(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = cwd / "input.txt"
        output_file = cwd / "output.txt"

        message = "Hello World!"

        sh = Shell.get_shell()

        cat = sh.command('cat')

        with input_file.open('w') as fout:
            fout.write(message)

        job = sh(
            cat.stdin(str(input_file)).stdout(str(output_file)).stderr(None),
            wait=False
        )[0]

        return_codes = job.wait()
        self.assertEqual(return_codes, [0])

        self.assertTrue(os.path.exists(str(output_file)))
        with output_file.open('r') as fin:
            observed = fin.read()

        self.assertEqual(message, observed)

