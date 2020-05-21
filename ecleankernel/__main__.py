# vim:fileencoding=utf-8
# (c) 2011-2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import argparse
import os
import os.path
import errno
import shlex
import subprocess
import sys
import time

from ecleankernel.bootloader import bootloaders, get_bootloader
from ecleankernel.kernel import Kernel
from ecleankernel.layout.std import StdLayout
from ecleankernel.process import get_removal_list

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


class NullDebugger(object):
    def __init__(self):
        self._indent = 1

    def print(self, msg):
        pass

    def printf(self, fstr, *args):
        self.print(fstr % args)

    def indent(self, n=1, heading=None):
        if heading is not None:
            self.print(heading)
        self._indent += n

    def outdent(self, n=1):
        self._indent -= n


class ConsoleDebugger(NullDebugger):
    def print(self, msg):
        ind = '*' * self._indent
        print('%s %s' % (ind, msg))


def main(argv):
    argp = argparse.ArgumentParser(description=ecleankern_desc.strip())
    argp.add_argument('-a', '--all',
                      action='store_true',
                      help='Remove all kernels unless used by bootloader')
    argp.add_argument('-A', '--ask',
                      action='store_true',
                      help='Ask before removing each kernel')
    argp.add_argument('-b', '--bootloader',
                      default='auto',
                      help='Bootloader used (auto, %s)'
                            % ', '.join([b.name for b in bootloaders]))
    argp.add_argument('-d', '--destructive',
                      action='store_true',
                      help='Destructive mode: remove kernels even when '
                           'referenced by bootloader')
    argp.add_argument('-D', '--debug',
                      action='store_true',
                      help='Enable debugging output')
    argp.add_argument('-l', '--list-kernels',
                      action='store_true',
                      help='List kernel files and exit')
    argp.add_argument('-M', '--no-mount',
                      action='store_false',
                      help='Disable (re-)mounting /boot if necessary')
    argp.add_argument('-n', '--num',
                      type=int,
                      default=0,
                      help='Leave only newest NUM kernels (by mtime)')
    argp.add_argument('-p', '--pretend',
                      action='store_true',
                      help='Print the list of kernels to be removed '
                           'and exit')
    argp.add_argument('-x', '--exclude',
                      default='',
                      help='Exclude kernel parts from being removed '
                           '(comma-separated, supported parts: %s)'
                           % ', '.join(Kernel.parts))

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

    exclusions = frozenset(args.exclude.split(','))
    for x in exclusions:
        if not x:
            pass
        elif x not in Kernel.parts:
            argp.error('Invalid kernel part: %s' % x)
        elif x == 'vmlinuz':
            argp.error('Kernel exclusion unsupported')

    debug = ConsoleDebugger() if args.debug else NullDebugger()

    bootfs = DummyMount()
    try:
        import pymountboot
    except ImportError:
        debug.print('unable to import pymountboot, /boot mounting disabled.')
    else:
        if args.mount:
            bootfs = pymountboot.BootMountpoint()

    try:
        try:
            bootfs.mount()
        except RuntimeError:
            raise MountError()

        try:
            layout = StdLayout()
            kernels = layout.find_kernels(exclusions=exclusions)

            if args.list_kernels:
                ordered = sorted(kernels,
                                 key=lambda k: k.mtime,
                                 reverse=True)
                for k in ordered:
                    print('%s [%s]:' % (k.version, k.real_kv))
                    for key in k.parts:
                        val = getattr(k, key)
                        if val is not None:
                            print('- %s: %s' % (key, val))
                    print('- last modified: %s' % time.strftime(
                        '%Y-%m-%d %H:%M:%S', time.gmtime(k.mtime)))
                return 0

            bootloader = get_bootloader(requested=args.bootloader,
                                        debug=debug)
            removals = get_removal_list(kernels,
                                        limit=None if args.all else args.num,
                                        bootloader=bootloader,
                                        destructive=args.destructive,
                                        debug=debug)

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

                for k, reason in removals:
                    print('- %s: %s' % (k.version, ', '.join(reason)))
                if has_kernel_install:
                    print('kernel-install will be called to perform'
                          + ' prerm tasks.')
                if removals and hasattr(bootloader, 'postrm'):
                    print('Bootloader %s config will be updated.' %
                          bootloader.name)
            else:
                bootfs.rwmount()
                for k, reason in removals:
                    k.check_writable()

                nremoved = 0

                for k, reason in removals:
                    remove = True
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
                            remove = False
                            break
                        else:
                            print('Invalid answer (%s).' % ans)

                    if remove:
                        print('* Removing kernel %s (%s)' %
                              (k.version, ', '.join(reason)))

                        if has_kernel_install:
                            cmd = ['kernel-install', 'remove']
                            if k.vmlinuz is not None:
                                cmd.extend([k.real_kv, k.vmlinuz])
                            else:
                                cmd.append(k.version)
                            p = subprocess.Popen(cmd)
                            if p.wait() != 0:
                                print('* kernel-install exited with'
                                      + '%d status' % p.returncode)

                        k.unrefall()
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
