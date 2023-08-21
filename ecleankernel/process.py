# vim:fileencoding=utf-8
# (c) 2011-2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import itertools
import logging
import os
import os.path
import typing

from pathlib import Path

from ecleankernel.bootloader import Bootloader
from ecleankernel.file import GenericFile, KernelImage
from ecleankernel.kernel import Kernel
from ecleankernel.sort import KernelSort


RemovableKernelDict = typing.Dict[Kernel, typing.List[str]]


class RemovableKernelFiles(typing.NamedTuple):
    kernel: Kernel
    reason: typing.List[str]
    files: typing.List[Path]


def get_removable_files(removed_kernels: RemovableKernelDict,
                        all_kernels: typing.Iterable[Kernel]
                        ) -> typing.Iterable[RemovableKernelFiles]:
    """
    Get list of actually removable files

    Scan kernels in `removed_kernels` for files common to both removed
    and non-removed kernels (using `all_kernels` as a reference),
    and return a generator of RemovableKernelFiles.
    """

    remaining_kernels = [k for k in all_kernels
                         if k not in removed_kernels]
    used_files = frozenset(
        f.path for f in itertools.chain.from_iterable(
            x.all_files for x in remaining_kernels))

    for k, reason in removed_kernels.items():
        files = [
            f.path for f in k.all_files
            if not any(os.path.samefile(f.path, of) for of in used_files)]
        yield RemovableKernelFiles(k, reason, files)


def remove_stray(kernels: typing.Iterable[Kernel]
                 ) -> typing.Iterable[Kernel]:
    """Remove files for non-existing kernels (without vmlinuz)"""
    for k in kernels:
        if not any(isinstance(f, KernelImage) for f in k.all_files):
            yield k


def get_removal_list(kernels: typing.List[Kernel],
                     sorter: KernelSort,
                     limit: typing.Optional[int] = 0,
                     bootloader: typing.Optional[Bootloader] = None,
                     destructive: bool = False
                     ) -> RemovableKernelDict:
    """
    Get list of kernel files to remove

    Apply requested filters on `kernels`, and return a generator
    of `RemovableKernel` tuples.  `limit` specifies how many newest
    kernels to keep, `bootloader` is the bootloader to reference
    in order to determine whether a kernel is used and `destructive`
    indicates whether bootloader references should be ignored.
    """

    logging.debug('in get_removal_list()')

    remove_kernels: typing.Dict[Kernel, typing.List[str]] = {}
    for k in remove_stray(kernels):
        remove_kernels.setdefault(k, []).append('vmlinuz does not exist')
    if len(remove_kernels) == len(kernels):
        raise SystemError(
            'No vmlinuz found. This seems ridiculous, aborting.')

    if limit is None or limit > 0:
        if not destructive:
            if bootloader is None:
                raise SystemError(f'Unable to get kernels from'
                                  f' bootloader config ({bootloader})')

            used_paths = frozenset(bootloader())

        if limit is not None:
            ordered = sorted(
                (k for k in kernels if k not in remove_kernels),
                key=sorter.key,
                reverse=True)
            candidates = ordered[limit:]
        else:
            candidates = kernels

        for k in candidates:
            def kernel_in_use(kernel_images: typing.List[GenericFile],
                              bootloader_used_kernels: typing.Iterable[str],
                              ) -> bool:
                for bp in bootloader_used_kernels:
                    for kernel_image in kernel_images:
                        try:
                            if kernel_image.path.samefile(bp):
                                return True
                        except FileNotFoundError:
                            pass
                return False

            if destructive:
                remove_kernels.setdefault(k, []).append('unwanted')
            elif not kernel_in_use(k.all_files, used_paths):
                assert bootloader is not None
                remove_kernels.setdefault(k, []).append(
                    f'not referenced by bootloader ({bootloader.name})')

    current = os.uname()[2]

    for k in list(remove_kernels):
        if k.version == current:
            print(f'Preserving currently running kernel ({current})')
            del remove_kernels[k]

    return remove_kernels
