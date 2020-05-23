# vim:fileencoding=utf-8
# (c) 2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import re
import typing

from ecleankernel.kernel import Kernel


class VersionSort(object):
    """Sort according to versions"""

    name = 'version'

    split_re = re.compile(r'(\d+|[a-zA-Z]+)')

    component_weights = {
        'old': -3,
        '~': -4,
        'rc': -5,
    }

    def key(self,
            k: Kernel
            ) -> tuple:
        """The key for sorting Kernels"""
        def process_comp(comp: typing.Iterable[str]
                         ) -> typing.Iterable[typing.Tuple[int, str]]:
            for c in comp:
                try:
                    yield (int(c), '')
                except (TypeError, ValueError):
                    pass
                try:
                    yield (self.component_weights[c], '')
                except KeyError:
                    pass
                # .M-foo sorts before .M.0
                yield (-1, c)
            yield (-2, '')  # terminator
        return tuple(process_comp(self.split_re.findall(k.version)))


class MTimeSort(object):
    """Sort according to mtimes"""

    name = 'mtime'

    def key(self,
            k: Kernel
            ) -> float:
        """The key for sorting Kernels"""
        return k.mtime
