# vim:fileencoding=utf-8
# (c) 2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import os
import typing

from pathlib import Path

from ecleankernel.file import (
    KernelFileType,
    GenericFile,
    KernelImage,
    UnrecognizedKernelError,
    EmptyDirectory,
    )
from ecleankernel.kernel import Kernel
from ecleankernel.layout.moduledir import ModuleDirLayout


class BlSpecLayout(ModuleDirLayout):
    """
    A layout implementing Bootloader Specification

    A Bootloader Spec layout, i.e. using /boot/[EFI/]<machine-id>
    directories.
    """

    name = 'blspec'
    potential_dirs = ('boot/EFI', 'boot')

    name_map = {
        'initrd': KernelFileType.INITRAMFS,
        'linux': KernelFileType.KERNEL,
    }

    @classmethod
    def get_boot_subdir(self,
                        root: Path
                        ) -> typing.Optional[Path]:
        """Get the /boot subdirectory for current machine (or None)"""
        try:
            with open(root / 'etc/machine-id') as f:
                machine_id = f.read().strip()
            for d in self.potential_dirs:
                bootdir = root / d / machine_id
                if bootdir.is_dir():
                    return bootdir
        except FileNotFoundError:
            pass
        return None

    @classmethod
    def is_acceptable(self,
                      root: Path = Path('/')
                      ) -> bool:
        return self.get_boot_subdir(root) is not None

    def find_kernels(self,
                     exclusions: typing.Container[KernelFileType] = [],
                     root: Path = Path('/')
                     ) -> typing.List[Kernel]:
        boot_subdir = self.get_boot_subdir(root)
        assert boot_subdir is not None

        # this would wreak havok all around the place
        assert KernelFileType.KERNEL not in exclusions

        # collect all module directories first
        module_dict = self.get_module_dict(
            exclusions=exclusions,
            module_directory=root / 'lib/modules')

        # collect from /boot
        kernels: typing.Dict[str, Kernel] = {}
        for ver in os.listdir(boot_subdir):
            if ver.startswith('.'):
                continue
            dir_path = boot_subdir / ver
            if dir_path.is_symlink() or not dir_path.is_dir():
                continue

            k = Kernel(ver)
            for fn in os.listdir(dir_path):
                if fn.startswith('.'):
                    continue
                path = dir_path / fn
                ftype = self.name_map.get(fn, KernelFileType.MISC)
                fobj = GenericFile(path, ftype)
                if ftype == KernelFileType.KERNEL:
                    try:
                        kobj = KernelImage(path)
                    except UnrecognizedKernelError:
                        pass
                    else:
                        # associate the module directory
                        k.all_files.extend(
                            module_dict.get(kobj.internal_version, []))
                        fobj = kobj
                if ftype not in exclusions:
                    k.all_files.append(fobj)
            k.all_files.append(EmptyDirectory(dir_path))
            kernels[ver] = k

        # merge unassociated modules into kernel groups
        for mkv, fobjs in module_dict.items():
            if any(mkv == k.real_kv for k in kernels.values()):
                continue
            kernels.setdefault(mkv, Kernel(mkv)).all_files.extend(fobjs)

        return list(kernels.values())
