# vim:fileencoding=utf-8
# (c) 2011-2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import os
import os.path
import re
import typing

from ecleankernel.kernel import Kernel


class RemovedKernelDict(dict):
    def add(self, k, reason):
        if k not in self:
            self[k] = ()
        self[k] += (reason,)

    def __iter__(self):
        return iter(self.items())


def remove_stray(kernels: typing.Iterable[Kernel]
                 ) -> typing.Iterable[Kernel]:
    """ Remove files for non-existing kernels (without vmlinuz). """
    for k in kernels:
        if k.vmlinuz is None:
            yield k


def get_removal_list(kernels: typing.List[Kernel],
                     debug: typing.Any,
                     limit: int = 0,
                     bootloader: typing.Optional[typing.Any] = None,
                     destructive: bool = False
                     ) -> typing.List[typing.Tuple[str, Kernel]]:
    """ Get a list of outdated kernels to remove. With explanations. """

    debug.indent(heading='In get_removal_list()')

    out = RemovedKernelDict()
    for k in remove_stray(kernels):
        out.add(k, 'vmlinuz does not exist')
    if len(out) == len(kernels):
        raise SystemError('No vmlinuz found. This seems ridiculous, aborting.')

    if limit is None or limit > 0:
        if not destructive:
            if bootloader is None:
                raise SystemError('Unable to get kernels from'
                                  + ' bootloader config (%s)'
                                  % bootloader)

            used = bootloader()
            realpaths = [os.path.realpath(x) for x in used]

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

            used = frozenset(unprefixify(realpaths))

        if limit is not None:
            ordered = sorted(kernels, key=lambda k: k.mtime, reverse=True)
            candidates = ordered[limit:]
        else:
            candidates = kernels

        for k in candidates:
            if destructive:
                out.add(k, 'unwanted')
            elif k.version not in used:
                assert bootloader is not None
                out.add(k, 'not referenced by bootloader (%s)' %
                        bootloader.name)

    current = os.uname()[2]

    def not_current(kre):
        if kre[0].version == current:
            print('Preserving currently running kernel (%s)' % current)
            return False
        return True

    debug.outdent()
    return list(filter(not_current, out))
