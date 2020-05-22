# vim:fileencoding=utf-8
# (c) 2011-2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import itertools
import os
import os.path
import re
import typing

from pathlib import Path

from ecleankernel.file import KernelImage
from ecleankernel.kernel import Kernel


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
        print(k.all_files)
        if not any(isinstance(f, KernelImage) for f in k.all_files):
            yield k


def get_removal_list(kernels: typing.List[Kernel],
                     debug: typing.Any,
                     limit: int = 0,
                     bootloader: typing.Optional[typing.Any] = None,
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

    debug.indent(heading='In get_removal_list()')

    remove_kernels: typing.Dict[Kernel, typing.List[str]] = {}
    for k in remove_stray(kernels):
        remove_kernels.setdefault(k, []).append('vmlinuz does not exist')
    if len(remove_kernels) == len(kernels):
        raise SystemError(
            'No vmlinuz found. This seems ridiculous, aborting.')

    if limit is None or limit > 0:
        if not destructive:
            if bootloader is None:
                raise SystemError('Unable to get kernels from'
                                  + ' bootloader config (%s)'
                                  % bootloader)

            used_paths = bootloader()

            prefix = re.compile(r'^/boot/(vmlinu[xz]|kernel|bzImage)-')
            ignored = re.compile(r'^/boot/xen')

            def unprefixify(filenames):
                for fn in filenames:
                    if not os.path.exists(fn):
                        print(
                            'Note: referenced kernel does not exist: %s' %
                            fn)
                    else:
                        kv, numsubs = prefix.subn('', fn)
                        if numsubs == 1:
                            yield kv
                        elif not ignored.match(fn):
                            print('Note: strangely named used kernel: %s' % fn)

            used = frozenset(unprefixify(used_paths))

        if limit is not None:
            ordered = sorted(kernels, key=lambda k: k.mtime, reverse=True)
            candidates = ordered[limit:]
        else:
            candidates = kernels

        for k in candidates:
            if destructive:
                remove_kernels.setdefault(k, []).append('unwanted')
            elif k.version not in used:
                assert bootloader is not None
                remove_kernels.setdefault(k, []).append(
                    'not referenced by bootloader (%s)'
                    % bootloader.name)

    current = os.uname()[2]

    for k in list(remove_kernels):
        if k.version == current:
            print('Preserving currently running kernel (%s)' % current)
            del remove_kernels[k]

    debug.outdent()
    return remove_kernels
