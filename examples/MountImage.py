"""
This example file is intended to demonstrate how to use SHTK to mount a Debian
or Ubuntu image and install vim inside it via chroot.  All mount points are
automatically unmounted after success or failure of installation.  

Args:
    image_path (str): Path of the image to mount
    mount_path (str): Path of the directory to mount on
"""

import contextlib
import pathlib
import sys

import shtk

class Mount:
    """
    Manages a mount.  Works so long as Python doesn't segfault or similar.

    Args:
        src_path (str or pathlib.Path): The device to mount from
        dst_path (str or pathlib.Path): The directory to mount on

    Raises:
        shtk.NonzeroExitCodeException:
            If the mount or unmount returns a non-zero exit code.
    """
    def __init__(self, src_path, dst_path, options=[]):
        self.src_path = str(src_path)
        self.dst_path = str(dst_path)
        self.options = list(options)

    def __enter__(self):
        sh = shtk.Shell.get_shell()
        mount = sh.command('mount', user='root')
        sh(mount(*self.options, "--", self.src_path, self.dst_path))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sh = shtk.Shell.get_shell()
        umount = sh.command('umount', user='root')
        sh(umount('-l', self.dst_path))

@contextlib.contextmanager
def PrepChroot(image_path, mount_path):
    """
    Mounts an image and prepares it for chroot usage

    Args:
        image_path (pathlib.Path or str): The image file to mount.
        mount_path (pathlib.Path or str): The directory on which to mount
            the image.

    Raises:
        shtk.NonzeroExitCodeException:
            If any mount or unmount returns a non-zero exit code.
    """
    image_path = pathlib.Path(image_path)
    mount_path = pathlib.Path(mount_path)
    with contextlib.ExitStack() as stack:
        stack.enter_context(Mount(image_path, mount_path, options=('-o', 'loop')))
        stack.enter_context(Mount('none', mount_path / 'proc', options=('-t', 'proc')))
        stack.enter_context(Mount('none', mount_path / 'sys', options=('-t', 'sysfs')))
        stack.enter_context(Mount('/dev', mount_path / 'dev', options=('--rbind',)))
        stack.enter_context(Mount('devpts', mount_path / 'dev' / 'pts', options=('-t', 'devpts')))
        stack.enter_context(Mount('/run', mount_path / 'run', options=('--rbind',)))

        yield stack

def main(image_path, mount_path):
    """
    Mounts an image and runs `chroot apt -y install vim`

    Args:
        image_path (pathlib.Path or str): The image file to mount.
        mount_path (pathlib.Path or str): The directory on which to mount
            the image.

    Raises:
        shtk.NonzeroExitCodeException:
            If any mount or unmount returns a non-zero exit code.
    """
    with shtk.Shell() as sh:
        with PrepChroot(image_path, mount_path):
            chroot = sh.command('chroot', user='root')
            sh(chroot('apt', '-y', 'install', 'vim'))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
