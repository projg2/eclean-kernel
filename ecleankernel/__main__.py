# vim:fileencoding=utf-8
# (c) 2011-2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import argparse
import logging
import os
import os.path
import shlex
import subprocess
import sys
import time
import typing

from pathlib import Path

from ecleankernel import __version__
from ecleankernel.bootloader import Bootloader, BootloaderNotFound
from ecleankernel.file import KernelImage, KernelFileType
from ecleankernel.layout import Layout, LayoutNotFound
from ecleankernel.process import get_removal_list, get_removable_files

from ecleankernel.bootloader.grub import GRUB
from ecleankernel.bootloader.grub2 import GRUB2
from ecleankernel.bootloader.lilo import LILO
from ecleankernel.bootloader.yaboot import Yaboot
from ecleankernel.bootloader.symlinks import Symlinks
from ecleankernel.layout.blspec import BlSpecLayout
from ecleankernel.layout.std import StdLayout
from ecleankernel.sort import MTimeSort, VersionSort

ecleankern_desc = '''
Remove old kernel versions, keeping either N newest kernels (with -n)
or only those which are referenced by a bootloader (with -a).
'''


class DummyMount(object):
    def mount(self) -> None:
        pass

    def rwmount(self) -> None:
        pass

    def umount(self) -> None:
        pass


class MountError(Exception):
    def __init__(self) -> None:
        Exception.__init__(self, 'Unable to mount /boot')

    @property
    def friendly_desc(self) -> str:
        return '''The program is unable to mount /boot.

This usually indicates that you have insufficient permissions to run
eclean-kernel, or your fstab is incorrect. Improperly mounted file-
systems can result in wrong files being removed, and therefore
eclean-kernel will refuse to proceed. Please either run the program
as root, or preferably mount /boot before using it.'''


def main(argv: typing.List[str]) -> int:
    kernel_parts = [x.value for x in KernelFileType.__members__.values()]
    bootloaders: typing.List[typing.Type[Bootloader]] = [
        LILO, GRUB2, GRUB, Yaboot, Symlinks]
    layouts: typing.List[typing.Type[Layout]] = [
        BlSpecLayout, StdLayout]
    sorts = [MTimeSort, VersionSort]

    argp = argparse.ArgumentParser(description=ecleankern_desc.strip())
    argp.add_argument('-V', '--version',
                      action='version',
                      version=__version__)

    group = argp.add_argument_group('action control')
    group.add_argument('-A', '--ask',
                       action='store_true',
                       help='Ask before removing each kernel')
    group.add_argument('-l', '--list-kernels',
                       action='store_true',
                       help='List kernel files and exit')
    group.add_argument('-p', '--pretend',
                       action='store_true',
                       help='Print the list of kernels to be removed '
                            'and exit')
    group.add_argument("--read-kernel-version",
                       type=Path,
                       metavar="KERNEL_PATH",
                       help="Read kernel version from the specified file, "
                            "print it and exit")

    group = argp.add_argument_group('system configuration')
    group.add_argument('-b', '--bootloader',
                       default='auto',
                       help=f'Bootloader used (auto, '
                            f'{", ".join(b.name for b in bootloaders)})')
    group.add_argument('-L', '--layout',
                       default='auto',
                       help=f'Layout used (auto, '
                            f'{", ".join(l.name for l in layouts)})')
    group.add_argument('-r', '--root',
                       type=Path,
                       default=Path('/'),
                       help='Alternate filesystem root to use')

    group = argp.add_argument_group('kernel selection')
    group.add_argument('-a', '--all',
                       action='store_true',
                       help='Remove all kernels unless used by bootloader')
    group.add_argument('-d', '--destructive',
                       action='store_true',
                       help='Destructive mode: remove kernels even when '
                            'referenced by bootloader')
    group.add_argument('-n', '--num',
                       type=int,
                       default=0,
                       help='Leave only newest NUM kernels (see also: '
                            '--sort-order)')
    group.add_argument('-s', '--sort-order',
                       default='version',
                       help=f'Kernel sort order ('
                            f'{", ".join(s.name for s in sorts)}); '
                            f'default: version')

    group = argp.add_argument_group('misc options')
    group.add_argument('-D', '--debug',
                       action='store_true',
                       help='Enable debugging output')
    group.add_argument('-M', '--no-mount',
                       action='store_true',
                       help='Disable (re-)mounting /boot if necessary')
    group.add_argument('--no-bootloader-update',
                       action='store_true',
                       help='Do not update bootloader configuration '
                            'after removing kernels (if supported '
                            'by the bootloader')
    group.add_argument('--no-kernel-install',
                       action='store_true',
                       help='Do not call kernel-install while removing '
                            'kernels (if installed)')
    group.add_argument('-x', '--exclude',
                       default='',
                       help=f'Exclude kernel parts from being removed '
                            f'(comma-separated, supported parts: '
                            f'{", ".join(kernel_parts)})')

    all_args = []
    config_dirs = os.environ.get('XDG_CONFIG_DIRS', '/etc/xdg').split(':')
    config_dirs.insert(0, os.environ.get('XDG_CONFIG_HOME', '~/.config'))
    for x in reversed(config_dirs):
        try:
            with open(Path(os.path.expanduser(x)) / 'eclean-kernel.rc',
                      'r') as f:
                all_args.extend(shlex.split(f.read(), comments=True))
        except FileNotFoundError:
            pass
        except NotADirectoryError:
            # XDG_CONFIG_* does not have to be correct
            pass

    all_args.extend(argv)
    args = argp.parse_args(all_args)

    exclusions = []
    for x in frozenset(args.exclude.split(',')):
        if not x:
            continue
        elif x not in kernel_parts:
            argp.error(f'Invalid kernel part: {x}')
        elif x == 'vmlinuz':
            argp.error('Kernel exclusion unsupported')
        exclusions.append(KernelFileType(x))

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    for sort_cls in sorts:
        if args.sort_order == sort_cls.name:
            break
    else:
        argp.error(f'Invalid sort order: {args.sort}')
    sorter = sort_cls()
    logging.debug(f'Sorter: {sorter}')

    bootfs = DummyMount()
    try:
        import pymountboot
    except ImportError:
        logging.debug('unable to import pymountboot, /boot mounting disabled.')
    else:
        if not args.no_mount:
            bootfs = pymountboot.BootMountpoint()

    try:
        try:
            bootfs.mount()
        except RuntimeError:
            raise MountError()

        if args.read_kernel_version is not None:
            print(KernelImage(args.read_kernel_version)
                  .read_internal_version())
            return 0

        for layout_cls in layouts:
            if args.layout in ('auto', layout_cls.name):
                try:
                    layout = layout_cls(root=args.root)
                    break
                except LayoutNotFound as e:
                    logging.debug(f'Layout failed: {layout_cls}; '
                                  f'exception: {e}')
        else:
            # auto should never fail -- std always succeeds
            assert args.layout != 'auto'
            argp.error(f'Invalid layout: {args.layout}')
        logging.debug(f'Layout: {layout}')

        bootloader: typing.Optional[Bootloader] = None
        for bootloader_cls in bootloaders:
            if args.bootloader == 'auto':
                try:
                    bootloader = bootloader_cls()
                    break
                except BootloaderNotFound:
                    logging.debug(f'Bootloader failed: {bootloader_cls}')
            elif args.bootloader == bootloader_cls.name:
                bootloader = bootloader_cls()
                break
        logging.debug(f'Bootloader: {bootloader}')

        try:
            kernels = layout.find_kernels(exclusions=exclusions)

            if args.list_kernels:
                ordered = sorted(kernels,
                                 key=sorter.key,
                                 reverse=True)
                for k in ordered:
                    print(f'{k.layout} {k.version} [{k.real_kv}]')
                    for kf in sorted(k.all_files, key=lambda f: f.path):
                        print(f'- {kf.ftype.value}: {kf.path}')
                    ts = time.strftime("%Y-%m-%d %H:%M:%S",
                                       time.gmtime(k.mtime))
                    print(f'- last modified: {ts}')
                return 0

            removals = get_removal_list(
                kernels,
                limit=None if args.all else args.num,
                sorter=sorter,
                bootloader=bootloader,
                destructive=args.destructive)

            has_kernel_install = False
            has_bootloader_postrm = False
            if args.root == Path('/'):
                if not args.no_kernel_install:
                    try:
                        (subprocess.Popen(['kernel-install', '--help'],
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
                                   .communicate())
                        has_kernel_install = True
                    except FileNotFoundError:
                        pass

                if (not args.no_bootloader_update
                        and bootloader is not None
                        and bootloader.has_postrm()):
                    has_bootloader_postrm = True

            if not removals:
                print('No outdated kernels found.')
                return 0

            print('Legend:')
            print('[-] file being removed')
            if not args.pretend:
                print('[x] file does not exist (anymore)')
            print('[+] file being kept (used by other kernels)')
            print()

            if args.pretend:
                print('These are the kernels which would be removed:')

                file_removals = list(
                    get_removable_files(removals, kernels))

                for k, reason, files in file_removals:
                    print(f'- {k.layout} {k.version}: {", ".join(reason)}')
                    for kf in k.all_files:
                        if kf.path in files:
                            sign = '-'
                        else:
                            sign = '+'
                        print(f' [{sign}] {kf.path}')
                if has_kernel_install:
                    print('kernel-install will be called to perform '
                          'prerm tasks.')
                if has_bootloader_postrm:
                    assert bootloader is not None
                    print(f'Bootloader {bootloader.name} config will '
                          f'be updated.')
            else:
                bootfs.rwmount()
                for k in removals:
                    k.check_writable()

                nremoved = 0

                for k, reason in list(removals.items()):
                    while args.ask:
                        ans = input(f'Remove {k.layout} {k.version} '
                                    f'({", ".join(reason)})? [Yes/No]'
                                    ).lower()
                        if 'yes'.startswith(ans):
                            break
                        elif 'no'.startswith(ans):
                            del removals[k]
                            break
                        else:
                            print(f'Unknown answer ({ans}).')

                file_removals = list(
                    get_removable_files(removals, kernels))

                for k, reason, files in file_removals:
                    print(f'* Removing kernel {k.layout} {k.version} '
                          f'({", ".join(reason)})')

                    if has_kernel_install:
                        cmd = ['kernel-install', 'remove']
                        for kf in k.all_files:
                            if isinstance(kf, KernelImage):
                                scmd = cmd + [kf.internal_version,
                                              str(kf.path)]
                                p = subprocess.Popen(scmd)
                                if p.wait() != 0:
                                    print(f'* kernel-install exited '
                                          f'with {p.returncode} status')

                    for kf in k.all_files:
                        if kf.path in files:
                            sign = '-'
                            if kf.path in files:
                                try:
                                    sign = '-' if kf.remove() else '+'
                                except FileNotFoundError:
                                    sign = 'x'
                        else:
                            sign = '+'
                        print(f' [{sign}] {kf.path}')
                    nremoved += 1

                if nremoved:
                    print(f'Removed {nremoved} kernels')
                    if has_bootloader_postrm:
                        assert bootloader is not None
                        bootloader.postrm()

            return 0
        finally:
            try:
                bootfs.umount()
            except RuntimeError:
                print('Note: unmounting /boot failed')
        return 0
    except Exception as e:
        if args.debug:
            raise
        print('eclean-kernel has met the following issue:\n')

        if hasattr(e, 'friendly_desc'):
            print(getattr(e, 'friendly_desc'))
        else:
            print(f'  {e!r}')

        print('''
If you believe that the mentioned issue is a bug, please report it
to https://github.com/mgorny/eclean-kernel/issues. If possible,
please attach the output of 'eclean-kernel --list-kernels' and your
regular eclean-kernel call with additional '--debug' argument.''')
        return 1


def setuptools_main() -> None:
    sys.exit(main(sys.argv[1:]))


if __name__ == '__main__':
    setuptools_main()
