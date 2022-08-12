import asyncio
import grp
import importlib.resources
import os
import pathlib
import pwd
import random
import sys
import unittest

from ...Job import NonzeroExitCodeException
from ...Shell import Shell
from ...StreamFactory import NullStreamFactory
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
            self.assertEqual(return_codes, (0,))

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
        tmpfile = cwd / "notexecutable.sh"

        tmpfile.touch(mode=0o600)

        with Shell(cwd=cwd) as sh:
            with self.assertRaises(RuntimeError):
                sh.command(f"./{tmpfile.name}")

@export
@register()
class TestCommandNotReadable(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        tmpfile = cwd / "notreadable.sh"

        tmpfile.touch(mode=0o300)

        with Shell(cwd=cwd) as sh:
            if os.getuid() != 0:
                with self.assertRaises(RuntimeError):
                    sh.command(f"./{tmpfile.name}")
            else:
                sh.command(f"./{tmpfile.name}")

@export
@register()
class TestNoEnvironment(TmpDirMixin):
    def runTest(self):
        with Shell(env={}) as sh:
            self.assertEqual(len(sh.environment), 0)

@export
@register()
class TestWithEnvironment(TmpDirMixin):
    def runTest(self):
        num_existing = len(os.environ)
        message = 'Hello World!'
        MESSAGE = 'MESSAGE'
        os.environ[MESSAGE] = message
        with Shell(env=os.environ, cwd=os.getcwd()) as sh:
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

        with Shell(cwd=cwd) as sh:
            cat = sh.command('cat')

            with (cwd / input_file).open('w') as fout:
                fout.write(message)

            job = sh(
                cat.stdin(str(input_file)).stdout(str(output_file)).stderr(None),
                wait=False
            )[0]

            return_codes = job.wait()
            self.assertEqual(return_codes, (0,))

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

        with Shell(cwd=cwd) as sh:
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
            with Shell(cwd=cwd) as sh:
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

        with Shell(cwd=cwd) as sh:
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

        with Shell(cwd=os.getcwd()) as sh:
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
            self.assertEqual(return_codes, (0,))

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
        self.assertEqual(return_codes, (0,))

        self.assertTrue(os.path.exists(str(output_file)))
        with output_file.open('r') as fin:
            observed = fin.read()

        self.assertEqual(message, observed)

@export
@register()
class TestRunAsDifferentUser(TmpDirMixin):
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
        outfile = cwd / "result.txt"

        with Shell(cwd=cwd, user=self.uid) as sh:
            cmd_id = sh.command(which('id'))
            sh.run(cmd_id('-u').stdout(outfile))
            with outfile.open('r') as fin:
                observed_uid = fin.read()
        self.assertEqual(observed_uid.strip(), str(self.uid))
        self.assertEqual(outfile.owner(), "nobody")

@export
@register()
class TestRunAsDifferentGroup(TmpDirMixin):
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
        outfile = cwd / "result.txt"

        with Shell(cwd=cwd, group=self.gid) as sh:
            cmd_id = sh.command(which('id'))
            sh.run(cmd_id('-g').stdout(outfile))
            with outfile.open('r') as fin:
                observed_gid = fin.read()
        self.assertEqual(observed_gid.strip(), str(self.gid))
        self.assertEqual(grp.getgrnam(outfile.group()).gr_gid, self.gid)

@export
@register()
class TestEvaluateAsDifferentUser(TmpDirMixin):
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

        with Shell(cwd=cwd, user=self.uid) as sh:
            cmd_id = sh.command(which('id'))
            observed_uid = sh.evaluate(cmd_id('-u'))
        self.assertEqual(observed_uid.strip(), str(self.uid))

@export
@register()
class TestEvaluateAsDifferentGroup(TmpDirMixin):
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

        with Shell(cwd=cwd, group=self.gid) as sh:
            cmd_id = sh.command(which('id'))
            observed_gid = sh.evaluate(cmd_id('-g'))
        self.assertEqual(observed_gid.strip(), str(self.gid))

@export
@register()
class TestShellSourceSuccess(TmpDirMixin):
    def setUp(self):
        super().setUp()

    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = cwd / 'test.sh'
        exp_val = random.randint(1024,1024*1024*1024)

        with input_file.open('w') as fout:
            print(f"""
TEST={exp_val!s}
export TEST
            """.strip(), file=fout)

        with Shell(cwd=cwd) as sh:
            sh.source(input_file)
            self.assertEqual(sh.environment.get('TEST'), str(exp_val))

@export
@register()
class TestShellRelativeSourceSuccess(TmpDirMixin):
    def setUp(self):
        super().setUp()

    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = 'test.sh'
        exp_val = random.randint(1024,1024*1024*1024)

        with (cwd / input_file).open('w') as fout:
            print(f"""
TEST={exp_val!s}
export TEST
            """.strip(), file=fout)

        with Shell(cwd=cwd) as sh:
            sh.source(input_file)
            self.assertEqual(sh.environment.get('TEST'), str(exp_val))

@export
@register()
class TestShellSourceFailure(TmpDirMixin):
    def setUp(self):
        super().setUp()

    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        input_file = cwd / 'test.sh'
        exp_val = random.randint(1024,1024*1024*1024)

        with open(os.devnull, 'wb') as devnull:
            with Shell(cwd=cwd, exceptions=True, stderr=devnull, stdout=devnull) as sh:
                with self.assertRaises(NonzeroExitCodeException):
                    sh.source(str(input_file))
