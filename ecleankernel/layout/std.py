# vim:fileencoding=utf-8
# (c) 2011-2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import itertools
import os
import os.path
import typing

from pathlib import Path

from ecleankernel.file import (
    KernelFileType,
    GenericFile,
    KernelImage,
    ModuleDirectory,
    UnrecognizedKernelError,
    )
from ecleankernel.kernel import Kernel


class StdLayout(object):
    """
    Standard /boot layout used by pre-systemd-boot bootloaders

    A standard /boot layout presuming that all kernel files are placed
    directly in /boot directory.
    """

    prefixes = [
        (KernelFileType.KERNEL, 'vmlinuz-'),
        (KernelFileType.KERNEL, '/vmlinux-'),
        (KernelFileType.KERNEL, 'kernel-'),
        (KernelFileType.KERNEL, 'bzImage-'),
        (KernelFileType.SYSTEM_MAP, 'System.map-'),
        (KernelFileType.CONFIG, 'config-'),
        (KernelFileType.INITRAMFS, 'initramfs-'),
        (KernelFileType.INITRAMFS, 'initrd-'),
    ]

    suffixes = [
        # initramfs
        '.img',

        # config
        '.bz2',
        '.gz',
        '.lz',
        '.xz',
    ]

    def find_kernels(self,
                     exclusions: typing.List[str] = [],
                     boot_directory: Path = Path('/boot'),
                     module_directory: Path = Path('/lib/modules')
                     ) -> typing.List[Kernel]:
        """
        Find all files and directories related to installed kernels

        Find all kernel files and related data and return a list
        of `Kernel` objects.  `exclusions` specifies kernel parts
        to ignore.  `boot_directory` and `module_directory` specify
        paths to find kernels in.
        """

        # collect all module directories first
        module_dict: typing.Dict[str, typing.List[GenericFile]] = {}
        try:
            diter = os.listdir(module_directory)
        except FileNotFoundError:
            pass
        else:
            for fn in diter:
                if fn.startswith('.'):
                    continue
                path = module_directory / fn
                if path.is_symlink() or not path.is_dir():
                    continue
                mlist = module_dict.setdefault(fn, [])
                mobj = ModuleDirectory(path)

                try:
                    mlist.append(GenericFile(
                        mobj.get_build_dir(), KernelFileType.BUILD))
                except FileNotFoundError:
                    pass

                # note: top directory must come last so that it isn't
                # removed before its subdirs
                mlist.append(mobj)

        # collect from /boot
        kernels: typing.Dict[str, typing.Dict[str, Kernel]] = {}
        other_files: typing.List[typing.Tuple[GenericFile, str]] = []
        try:
            diter = os.listdir(boot_directory)
        except FileNotFoundError:
            pass
        else:
            for fn in diter:
                if fn.startswith('.'):
                    continue
                path = boot_directory / fn
                if path.is_symlink() or not path.is_file():
                    continue
                # skip unversioned files
                ver = fn.partition('-')[2]
                if not ver:
                    continue

                # strip suffix from filename to get the correct version
                for suffix in self.suffixes:
                    if ver.endswith(suffix):
                        ver = ver[:-len(suffix)]
                        break
                    elif ver.endswith(suffix + '.old'):
                        ver = ver[:-len(suffix)-4] + '.old'

                # try recognizing kernel image via magic
                try:
                    kobj = KernelImage(path)
                except UnrecognizedKernelError:
                    # fall back to filename
                    for ftype, prefix in self.prefixes:
                        if fn.startswith(prefix):
                            other_files.append(
                                (GenericFile(path, ftype), ver))
                            break
                    continue

                # the following is done only for kernel images
                assert isinstance(kobj, KernelImage)
                kg = kernels.setdefault(ver, {})
                k = kg.setdefault(kobj.internal_version, Kernel(ver))
                k.all_files.append(kobj)

                # associate the module directory
                k.all_files.extend(
                    module_dict.get(kobj.internal_version, []))

        # merge other files into kernel groups
        for fobj, ver in other_files:
            kg = kernels.setdefault(ver, {})
            # if we had some images with matching apparent version,
            # append to all of their Kernels; if we had none, create
            # a single Kernel object
            if not kg:
                kg[''] = Kernel(ver)
            for k in kg.values():
                k.all_files.append(fobj)

        # merge unassociated modules into kernel groups
        for mkv, fobjs in module_dict.items():
            if any(mkv == kv for kg in kernels.values() for kv in kg):
                continue
            (kernels.setdefault(mkv, {}).setdefault('', Kernel(mkv))
             .all_files.extend(fobjs))

        return list(
            itertools.chain.from_iterable(
                kg.values() for kg in kernels.values()))
