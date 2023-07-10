# vim:fileencoding=utf-8
# (c) 2020-2023 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import logging
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
from ecleankernel.layout import LayoutNotFound
from ecleankernel.layout.moduledir import ModuleDirLayout


class BlSpecLayout(ModuleDirLayout):
    """
    A layout implementing Bootloader Specification

    A Bootloader Spec layout, i.e. using /boot/[EFI/]<machine-id>
    directories.
    """

    name = 'blspec'
    potential_dirs = ('boot/EFI', 'boot/efi', 'boot', 'efi')

    name_map = {
        'initrd': KernelFileType.INITRAMFS,
        'linux': KernelFileType.KERNEL,
    }

    def __init__(self,
                 root: Path
                 ) -> None:
        super().__init__(root)
        # TODO: according to bootctl(1), we should fall back to IMAGE_ID=
        # and then ID= from os-release
        for path in ("etc/kernel/entry-token", "etc/machine-id"):
            try:
                with open(root / path) as f:
                    self.kernel_id = f.read().strip()
                break
            except FileNotFoundError:
                pass
        else:
            raise LayoutNotFound("/etc/machine-id not found")

        for d in self.potential_dirs:
            bootloaderdir = root / d / "loader"
            if bootloaderdir.is_dir():
                # Type 1 entries (linux+initrd) are in
                # $BOOT/ENTRY-TOKEN/KERNEL-VERSION/
                self.blsdir = root / d / self.kernel_id
                # Type 2 entries (uki's) are in
                # $BOOT/EFI/Linux/ENTRY-TOKEN-KERNEL-VERSION.efi
                self.ukidir = root / d / "EFI" / "Linux"
                return
        else:
            raise LayoutNotFound("/boot/[EFI/]loader not found")

    def append_kernel_files(self,
                            ftype: KernelFileType,
                            path: Path,
                            k: Kernel,
                            ver: str,
                            module_dict: dict,
                            exclusions: typing.Container[KernelFileType] = [],
                            ) -> Kernel:
        fobj = GenericFile(path, ftype)

        if ftype == KernelFileType.KERNEL:
            try:
                kobj = KernelImage(path)
            except UnrecognizedKernelError as err:
                logging.debug(
                    f"Unrecognized potential kernel image: {err}")
            else:
                fobj = kobj
                # associate the module directory
                k.all_files.extend(
                    module_dict.get(kobj.internal_version, []))

        if ftype not in exclusions:
            k.all_files.append(fobj)

        return k

    def find_kernels(self,
                     exclusions: typing.Container[KernelFileType] = [],
                     ) -> typing.List[Kernel]:
        # this would wreak havok all around the place
        assert KernelFileType.KERNEL not in exclusions

        # collect all module directories first
        module_dict = self.get_module_dict(
            exclusions=exclusions,
            module_directory=self.root / 'lib/modules')

        # collect from /boot
        kernels: typing.Dict[typing.Tuple[str, str], Kernel] = {}
        if self.blsdir.is_dir():
            for ver in os.listdir(self.blsdir):
                if ver.startswith('.'):
                    continue
                dir_path = self.blsdir / ver
                if dir_path.is_symlink() or not dir_path.is_dir():
                    continue

                k = Kernel(ver, layout="bls")

                for fn in os.listdir(dir_path):
                    if fn.startswith('.'):
                        continue
                    kernels[(ver, "bls")] = self.append_kernel_files(
                        self.name_map.get(fn, KernelFileType.MISC),
                        dir_path / fn,
                        k, ver, module_dict, exclusions)
                kernels[(ver, "bls")].all_files.append(
                    EmptyDirectory(dir_path))

        # collect from ESP/Linux
        if self.ukidir.is_dir():
            for file in os.listdir(self.ukidir):
                if (not file.startswith(self.kernel_id) or
                        not file.endswith(".efi")):
                    # This file is not an efi file or does not belong to us
                    continue
                ver = file.removeprefix(self.kernel_id +
                                        "-").removesuffix(".efi")

                kernels[(ver, "uki")] = self.append_kernel_files(
                        KernelFileType.KERNEL,
                        self.ukidir / file,
                        Kernel(ver, layout="uki"),
                        ver, module_dict,
                        exclusions)

        # merge unassociated modules into kernel groups
        for mkv, fobjs in module_dict.items():
            if any(mkv == k.real_kv for k in kernels.values()):
                continue
            # this mkv does not have a corresponding kernel
            # with same real_kv in kernels
            match_found = False
            for (ver, layout), k in kernels.items():
                if ver == mkv:
                    # extend existing entry
                    k.all_files.extend(fobjs)
                    match_found = True
            if not match_found:
                # no real_kv for this mkv, no existing entry in kernels
                layout = "modules-only"
                kernels.setdefault((mkv, layout),
                                   Kernel(mkv, layout=layout)
                                   ).all_files.extend(fobjs)

        return list(kernels.values())
