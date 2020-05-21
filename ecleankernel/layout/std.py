# vim:fileencoding=utf-8
# (c) 2011-2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import os.path
import typing

from glob import glob

from ecleankernel.kernel import KernelDict, PathDict


class StdLayout(object):
    """
    Standard /boot layout used by pre-systemd-boot bootloaders

    A standard /boot layout presuming that all kernel files are placed
    directly in /boot directory.
    """

    def find_kernels(self,
                     exclusions: typing.List[str] = [],
                     boot_directory: str = '/boot',
                     module_directory: str = '/lib/modules'
                     ) -> KernelDict:
        """
        Find all files and directories related to installed kernels

        Find all kernel files and related data and return them
        as a `KernelDict`.  `exclusions` specifies kernel parts
        to ignore.  `boot_directory` and `module_directory` specify
        paths to find kernels in.
        """

        globs = [
            ('vmlinuz', f'{boot_directory}/vmlinuz-'),
            ('vmlinuz', f'{boot_directory}/vmlinux-'),
            ('vmlinuz', f'{boot_directory}/kernel-'),
            ('vmlinuz', f'{boot_directory}/bzImage-'),
            ('systemmap', f'{boot_directory}/System.map-'),
            ('config', f'{boot_directory}/config-'),
            ('initramfs', f'{boot_directory}/initramfs-'),
            ('initramfs', f'{boot_directory}/initrd-'),
            ('modules', f'{module_directory}/'),
        ]

        # paths can repeat, so keep them sorted
        paths = PathDict()

        kernels = KernelDict()
        for cat, g in globs:
            if cat in exclusions:
                continue
            for m in glob('%s*' % g):
                kv = m[len(g):]
                if cat == 'initramfs' and kv.endswith('.img'):
                    kv = kv[:-4]
                elif cat == 'modules' and m in paths:
                    continue

                path = paths[m]
                newk = kernels[kv]
                try:
                    setattr(newk, cat, path)
                except KeyError:
                    raise SystemError('Colliding %s files: %s and %s'
                                      % (cat, m, getattr(newk, cat)))

                if cat == 'modules':
                    builddir = paths[os.path.join(path, 'build')]
                    if os.path.isdir(builddir):
                        newk.build = builddir

                    if '%s.old' % kv in kernels:
                        kernels['%s.old' % kv].modules = path
                        if newk.build:
                            kernels['%s.old' % kv].build = builddir
                if cat == 'vmlinuz':
                    realkv = newk.real_kv
                    moduledir = os.path.join('/lib/modules', realkv)
                    builddir = paths[os.path.join(moduledir, 'build')]
                    if ('modules' not in exclusions
                            and os.path.isdir(moduledir)):
                        newk.modules = paths[moduledir]
                    if ('build' not in exclusions
                            and os.path.isdir(builddir)):
                        newk.build = paths[builddir]

        # fill .old files
        for k in kernels:
            if '%s.old' % k.version in kernels:
                oldk = kernels['%s.old' % k.version]
                # it seems that these are renamed .old sometimes
                if not oldk.systemmap and k.systemmap:
                    oldk.systemmap = k.systemmap
                if not oldk.config and k.config:
                    oldk.config = k.config

        return kernels
