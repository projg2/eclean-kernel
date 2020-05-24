# vim:fileencoding=utf-8
# (c) 2011-2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import os
import typing

from pathlib import Path

from ecleankernel.file import (
    KernelFileType,
    GenericFile,
    GenericDirectory,
    ModuleDirectory,
    )
from ecleankernel.layout import Layout


class ModuleDirLayout(Layout):
    """A common class for layouts using a module-dir"""

    def get_module_dict(self,
                        exclusions: typing.Container[KernelFileType],
                        module_directory: Path
                        ) -> typing.Dict[str, typing.List[GenericFile]]:
        """Get dict of module directories found in /lib/modules"""
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

                if KernelFileType.BUILD not in exclusions:
                    try:
                        build = mobj.get_build_dir()
                        if build.is_dir():
                            mlist.append(GenericDirectory(
                                build, KernelFileType.BUILD))
                    except FileNotFoundError:
                        pass

                # note: top directory must come last so that it isn't
                # removed before its subdirs
                if KernelFileType.MODULES not in exclusions:
                    mlist.append(mobj)
        return module_dict
