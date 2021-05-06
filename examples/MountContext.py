# -*- coding: utf-8 -*-
"""
Context managers and other utilities for mounting partitions from python.
"""

import contextlib
import os
import pathlib
import time

import parted

import shtk

def find_partition(parted_disk, name=None, number=None):
    """
    Finds a partition within a pyparted disk

    Returns the first partition matching all requirements whose value is not
    None.  If no partitions match all requirements, then None is returned.

    Args:
        parted_disk (parted.Disk): a Disk object built by pyparted
        name (None or str): the name of the partition
        number (None or str): the partition number

    Returns:
        None or parted.Partition:
            The first matching partition (or None)
    """

    def match(expected, observed):
        if expected is None:
            return None
        return expected == observed

    for partition in parted_disk.partitions:
        tests = []

        tests.append(match(name, partition.name))
        tests.append(match(number, partition.number))

        if not any(test is False for test in tests):
            return partition

    return None

class LoopbackContext:
    """
    Context manager that calls losetup to create a temporary loopback device

    Creates a new loopback device using losetup upon __enter__().  Deletes the
    loopback device upon __exit__().

    Attributes:
        filepath (str or pathlib.Path): The path of the source file
        offset (int): The offset (in bytes) from the beginning of the source
            file
        sizelimit (int): The maximum size (in bytes) of the new loopback device
        device (None or str): The filepath of the new loopback device (None
            prior to __enter__() and after __exit__())

    """
    def __init__(self, filepath, offset, sizelimit):
        """
        filepath (str): The path of the source file
        offset (int): The offset (in bytes) from the beginning of the source
            file
        sizelimit (int): The maximum size (in bytes) of the new loopback device
        """

        self.filepath = pathlib.Path(filepath)
        self.offset = int(offset)
        self.sizelimit = int(sizelimit)
        self.device = None

    def __enter__(self):
        """
        Calls the losetup command to create a new loopback device.

        Returns:
            str:
                The filepath of the temporary loopback device
        """
        shell = shtk.Shell.get_shell()
        losetup = shell.command('losetup')
        self.device = shell.evaluate(
            losetup(
                '--find', '--show',
                '--offset', str(self.offset),
                '--sizelimit', str(self.sizelimit),
                self.filepath
            )
        ).strip()

        return self

    def __exit__(self, *exc):
        """
        Calls the losetup command to delete the new loopback device

        Args:
            exc (list): list of unused exception information (exc_type,
                exc_val, exc_tb)

        Returns:
            None:
                Does not suppress exceptions
        """

        shell = shtk.Shell.get_shell()
        losetup = shell.command('losetup')
        shell(
            losetup('-d', self.device)
        )

    @classmethod
    def from_partition(cls, filepath, name=None, number=None):
        """
        Factory method creating a loopback_context from a partition table

        Args:
            filepath (str or pathlib.Path): the location of the partition table
            name (str or None): the name of the partition to mount.  Note that
                this must be the partition label (or similar).  Filesystem
                labels won't work.
            number (int or None): the number of the partition to mount.  Note
                that disk numbers may differ from the order of the partitions
                within the partition table.

        Raises:
            RuntimeError:
                When no matching partition is found

        Returns:
            LoopbackContext:
                A new instance of LoopbackContext bound to the first matching
                    parititon.
        """

        device = parted.getDevice(filepath)
        disk = parted.newDisk(device)
        part = find_partition(disk, name=name, number=number)
        if part is None:
            raise RuntimeError("Failed to find matching partition within partition table")
        offset = part.geometry.start * part.geometry.device.sectorSize
        return cls(pathlib.Path(filepath), offset=offset, sizelimit=part.getLength('B'))

class MountContext:
    """
    Context manager that calls mount and umount to temporarily mount a device

    Attributes:
        source (str or pathlib.Path): the source filepath for the mount command
        target (str or pathlib.Path): the destination directory for the mount
            command
        args (list of str): the arguments passed to the mount command
        missing_ok (boolean): whether the target directory should be created if
            it doesn't exist.
        cleanup_missing (boolean): whether the target directory should be
            removed if it was created by MountContext as a result of
            missing_ok.
        rmdir_target (boolean): whether the target diretory should be deleted
            upon unmounting (set upon mounting)
    """
    def __init__(self,
        source, target, types=None, options=None, bind=None, rbind=None,
        missing_ok=False, cleanup_missing_target=True, umount_recursive=False,
    ):
        """
        Constructor for MountContext

        Args:
            source (str): the source filepath for the mount command
            target (str): the destination directory for the mount command
            types (list of str): allowable filesystem types for the mount
            options (list of str): extra arguments passed to the mount command
            bind (boolean): adds '--bind' to the mount command's args when True
            rbind (boolean): adds '--rbind' to the mount command's args when
                True.  Implicitly sets umount_recursive.
            missing_ok (boolean): create the target directory if it doesn't
                exist
            umount_recursive (boolean): force a recursive unmount
            cleanup_missing_target (boolean): whether we should delete the
                target after use if we created it while mounting (see
                missing_ok).
        """
        if os.geteuid() != 0:
            raise RuntimeError("You must be root to mount volumes")

        self.source = pathlib.Path(source)
        self.target = pathlib.Path(target)
        self.missing_ok = missing_ok
        self.cleanup_missing_target = cleanup_missing_target
        self.rmdir_target = False

        self.args = []

        if bind:
            self.args.append("--bind")

        if rbind:
            self.args.append("--rbind")

        if rbind or umount_recursive:
            self.umount_recursive = True
        else:
            self.umount_recursive = False

        if types:
            self.args.extend(('--types', ",".join(str(x) for x in types)))

        if options:
            self.args.extend(("--options", ",".join(str(x) for x in options)))

        self.args.append(str(source))
        self.args.append(str(target))

    def __enter__(self):
        """
        Calls the losetup command to create a new loopback device.

        Returns:
            MountContext:
                self
        """
        shell = shtk.Shell.get_shell()
        mount = shell.command('mount')

        if not self.target.exists():
            if self.missing_ok:
                self.rmdir_target = self.cleanup_missing_target
                self.target.mkdir(exist_ok=True)
            else:
                raise RuntimeError(f"Directory {self.target!s} does not exist")
        else:
            self.rmdir_target = False

        if not self.target.is_dir():
            raise RuntimeError(f"{self.target!s} is not a directory")

        shell(
            mount(*self.args)
        )

        if '--rbind' in self.args:
            time.sleep(0.5) # Wait for make-rslave to propagate
            shell(
                mount('--make-rslave', self.target)
            )

        return self

    def __exit__(self, *exc):
        """
        Calls the umount command to unmount the target mount path

        Args:
            exc (list): list of unused exception information (exc_type,
                exc_val, exc_tb)

        Returns:
            None:
                Does not suppress exceptions
        """
        shell = shtk.Shell.get_shell()
        umount = shell.command('umount')
        if self.umount_recursive:
            shell(
                umount('--recursive', self.target)
            )
        else:
            shell(
                umount(self.target)
            )
        if self.rmdir_target:
            os.rmdir(self.target)

class ManyMountContext(contextlib.ExitStack):
    """
    A subclass of contextlib.ExitStack() with a helper method for mounting
    """
    def mount(self, source, target, part_name=None, part_number=None, **kwargs):
        """
        Creates a new MountContext and adds it to the context stack

        If part_name or part_number are provided, source will be assumed to be
        a partition table image, rather than a raw parititon.  An individual
        partition will be found and bound to a loopback device using
        losetup.from_partition(source, name=part_name, number=part_number).

        All additional keyword arguments are forwarded to MountContext().

        Args:
            source (str): the source filepath for the mount command
            target (str): the destination directory for the mount command
            part_name (str): the name of the partition to mount
            part_number (int): the number of the partition to mount
        """

        if part_name is not None or part_number is not None:
            loop = LoopbackContext.from_partition(source, name=part_name, number=part_number)
            loop = self.enter_context(loop)
            self.enter_context(
                MountContext(
                    source=loop.device,
                    target=target,
                    **kwargs
                )
            )
        else:
            self.enter_context(MountContext(source = source, target = target, **kwargs))

class ChrootMountContext(ManyMountContext):
    """
    A subclass of ManyMountContext that bind mounts essential directories

    Upon enter'ing the context the directories target/{dev,proc,sys} are
    mounted sequentially using the --rbind to the mount command.  The umount
    command will unmount them upon __exit__().

    If the directories target/{dev,proc,sys} do not exist they will be created
    only if the instance is initialized with missing_ok=True.

    Attributes:
        target (str): target directory to bind directories within
        source (str): source directory to bind-mount from
        missing_ok (boolean): when true, missing directories under target will
            be created automatically
    """

    def __init__(self, target, source='/', missing_ok=False):
        super().__init__()

        self.source = pathlib.Path(source)
        self.target = pathlib.Path(target)
        self.missing_ok = missing_ok

    def __enter__(self):
        """
        Bind-mounts the subdirectories target/{dev,proc,sys} using a
        MountContext and adds the context to the internal exit stack.

        Returns:
            ChrootMountContext:
                self
        """
        super().__enter__()

        self.mount(
            source = self.source / 'proc',
            target = self.target / 'proc',
            types = ['proc'],
            missing_ok = self.missing_ok
        )

        self.mount(
            source = self.source / 'sys',
            target = self.target / 'sys',
            types = ['sysfs'],
            missing_ok = self.missing_ok
        )

        self.mount(
            source = self.source / 'dev',
            target = self.target / 'dev',
            rbind = True,
            missing_ok = self.missing_ok
        )

        return self

if __name__ == "__main__":
    import sys
    with ManyMountContext() as mnt:
        src = sys.argv[1]
        dst = sys.argv[2]
        mnt.mount(src, dst, missing_ok=True, part_number=1)
        mnt.enter_context(ChrootMountContext(dst))
        print("Press Control+C to exit")
        while 1:
            time.sleep(60) # Wait for control+c
