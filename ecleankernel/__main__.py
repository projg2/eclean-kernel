# vim:fileencoding=utf-8
# (c) 2011-2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import argparse
import logging
import os
import os.path
import errno
import shlex
import shutil
import subprocess
import sys
import time

from pathlib import Path

from ecleankernel import __version__
from ecleankernel.bootloader import bootloaders, get_bootloader
from ecleankernel.file import KernelImage, KernelFileType
from ecleankernel.layout.blspec import BlSpecLayout
from ecleankernel.layout.std import StdLayout
from ecleankernel.process import get_removal_list, get_removable_files
from ecleankernel.sort import MTimeSort, VersionSort

ecleankern_desc = '''
Remove old kernel versions, keeping either N newest kernels (with -n)
or only those which are referenced by a bootloader (with -a).
'''


class DummyMount(object):
    def mount(self):
        pass

    def rwmount(self):
        pass

    def umount(self):
        pass


class MountError(Exception):
    def __init__(self):
        Exception.__init__(self, 'Unable to mount /boot')

    @property
    def friendly_desc(self):
        return '''The program is unable to mount /boot.

This usually indicates that you have insufficient permissions to run
eclean-kernel, or your fstab is incorrect. Improperly mounted file-
systems can result in wrong files being removed, and therefore
eclean-kernel will refuse to proceed. Please either run the program
as root, or preferably mount /boot before using it.'''


def main(argv):
    kernel_parts = [x.value for x in KernelFileType.__members__.values()]
    layouts = [BlSpecLayout, StdLayout]
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
                       action='store_false',
                       help='Disable (re-)mounting /boot if necessary')
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
            f = open('%s/eclean-kernel.rc' % os.path.expanduser(x), 'r')
        except IOError as e:
            if e.errno != errno.ENOENT:
                raise
        else:
            all_args.extend(shlex.split(f.read(), comments=True))

    all_args.extend(argv)
    args = argp.parse_args(all_args)

    exclusions = []
    for x in frozenset(args.exclude.split(',')):
        if not x:
            continue
        elif x not in kernel_parts:
            argp.error('Invalid kernel part: %s' % x)
        elif x == 'vmlinuz':
            argp.error('Kernel exclusion unsupported')
        exclusions.append(KernelFileType(x))

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    for layout_cls in layouts:
        if (args.layout == 'auto'
                and layout_cls.is_acceptable(root=args.root)):
            break
        elif args.layout == layout_cls.name:
            break
    else:
        argp.error(f'Invalid layout: {args.layout}')
    layout = layout_cls()

    for sort_cls in sorts:
        if args.sort_order == sort_cls.name:
            break
    else:
        argp.error(f'Invalid sort order: {args.sort}')
    sorter = sort_cls()

    bootfs = DummyMount()
    try:
        import pymountboot
    except ImportError:
        logging.debug('unable to import pymountboot, /boot mounting disabled.')
    else:
        if args.mount:
            bootfs = pymountboot.BootMountpoint()

    try:
        try:
            bootfs.mount()
        except RuntimeError:
            raise MountError()

        try:
            kernels = layout.find_kernels(exclusions=exclusions,
                                          root=args.root)

            if args.list_kernels:
                ordered = sorted(kernels,
                                 key=sorter.key,
                                 reverse=True)
                for k in ordered:
                    print(f'{k.version} [{k.real_kv}]')
                    for f in k.all_files:
                        print(f'- {f.ftype.value}: {f.path}')
                    ts = time.strftime("%Y-%m-%d %H:%M:%S",
                                       time.gmtime(k.mtime))
                    print(f'- last modified: {ts}')
                return 0

            bootloader = get_bootloader(requested=args.bootloader)
            removals = get_removal_list(
                kernels,
                limit=None if args.all else args.num,
                sorter=sorter,
                bootloader=bootloader,
                destructive=args.destructive)

            has_kernel_install = False
            try:
                subprocess.Popen(['kernel-install', '--help'],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE).communicate()
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise
            else:
                has_kernel_install = True

            if not removals:
                print('No outdated kernels found.')
            elif args.pretend:
                print('These are the kernels which would be removed:')

                file_removals = list(
                    get_removable_files(removals, kernels))

                for k, reason, files in file_removals:
                    print('- %s: %s' % (k.version, ', '.join(reason)))
                    for f in k.all_files:
                        if f.path in files:
                            sign = '-'
                        else:
                            sign = '+'
                        print(f' [{sign}] {f.path}')
                if has_kernel_install:
                    print('kernel-install will be called to perform'
                          + ' prerm tasks.')
                if hasattr(bootloader, 'postrm'):
                    print('Bootloader %s config will be updated.' %
                          bootloader.name)
            else:
                bootfs.rwmount()
                for k in removals:
                    k.check_writable()

                nremoved = 0

                for k, reason in list(removals.items()):
                    while args.ask:
                        try:
                            input_f = raw_input
                        except NameError:
                            input_f = input

                        ans = input_f('Remove %s (%s)? [Yes/No]'
                                      % (k.version, ', '.join(reason))).lower()
                        if 'yes'.startswith(ans):
                            break
                        elif 'no'.startswith(ans):
                            del removals[k]
                            break
                        else:
                            print('Invalid answer (%s).' % ans)

                file_removals = list(
                    get_removable_files(removals, kernels))

                for k, reason, files in file_removals:
                    print('* Removing kernel %s (%s)' %
                          (k.version, ', '.join(reason)))

                    if has_kernel_install:
                        # TODO: kernel-install will remove modules
                        # when it's not meant to
                        cmd = ['kernel-install', 'remove']
                        for kf in k.all_files:
                            if isinstance(kf, KernelImage):
                                scmd = cmd + [kf.internal_version,
                                              str(kf.path)]
                                p = subprocess.Popen(scmd)
                                if p.wait() != 0:
                                    print('* kernel-install exited with'
                                          + '%d status' % p.returncode)

                    for f in k.all_files:
                        if f.path in files:
                            sign = '-'
                        else:
                            sign = '+'
                        print(f' [{sign}] {f.path}')
                        if f.path in files:
                            if os.path.isdir(f.path):
                                shutil.rmtree(f.path)
                            else:
                                os.unlink(f.path)
                    nremoved += 1

                if nremoved:
                    print('Removed %d kernels' % nremoved)
                    if hasattr(bootloader, 'postrm'):
                        bootloader.postrm()

            return 0
        finally:
            try:
                bootfs.umount()
            except RuntimeError:
                print('Note: unmounting /boot failed')
    except Exception as e:
        if args.debug:
            raise
        print('eclean-kernel has met the following issue:\n')

        if hasattr(e, 'friendly_desc'):
            print(e.friendly_desc)
        else:
            print('  %r' % e)

        print('''
If you believe that the mentioned issue is a bug, please report it
to https://github.com/mgorny/eclean-kernel/issues. If possible,
please attach the output of 'eclean-kernel --list-kernels' and your
regular eclean-kernel call with additional '--debug' argument.''')


def setuptools_main() -> None:
    sys.exit(main(sys.argv[1:]))


if __name__ == '__main__':
    setuptools_main()
