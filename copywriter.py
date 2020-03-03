"""
Utility for adding and updating copyright notices on files.
"""
import argparse
import fnmatch
import glob
import os
from pathlib import Path
import itertools
import re
import subprocess as sub
import typing as ty


YEAR_PATTERN = '[0-9]{4}( *-? *[0-9]{4})?'
COPYRIGHT_REGEX = 'Copyright .*'


PathLike = ty.Union[str, os.PathLike, Path]


class Copywriter:
    def __init__(
            self,
            *root: PathLike,
            copyright_re: str = COPYRIGHT_REGEX,
            update_re: str = '',
    ) -> None:
        """
        Create new copywriter instance.

        Passed settings will be used for checking, updating, or adding
        copyright header notices.

        :param root: Paths of files or directories to search for
                    outdated or missing headers.
        :param header: Header str. (Ex: 'Copyright {years} ')
        """
        self.roots = [Path(path) for path in root]
        self.copyright_re = copyright_re
        self.update_re = update_re

        self.files = self._find_files(*self.roots)
        self._outdated: ty.Optional[ty.Set[Path]] = None
        self._missing: ty.Optional[ty.Set[Path]] = None

    @staticmethod
    def _find_files(*root: PathLike) -> ty.Set[Path]:
        """
        Finds files of recognized types.

        Given an iterable of roots at which to begin searching, returns
        all files of recognizable type.

        Any number of the passed roots may instead point to a specific
        file, in which case the file will be returned if it
        is recognized.

        :param root: Paths at which to begin search.
        :return: List[Path]
        """
        patterns = list(itertools.chain(
            *(t.patterns for t in file_types.values())
        ))
        paths = {path for path in root if path.is_file() and recognize(path)}
        for root_ in filter(Path.is_dir, root):
            for f_pat in patterns:
                paths |= {
                    Path(s) for s in
                    glob.glob(f'{root_}/**/{f_pat}', recursive=True)
                }

        return paths

    def show(self) -> None:
        """
        Print to stdout all files that are in need of changes.
        :return: None
        """
        old = self.outdated
        missing = self.missing
        if old:
            print(f'Old copyright headers: {fmt_file_list(old)}')
        if missing:
            print(f'Missing copyright headers: {fmt_file_list(missing)}')
        if old:
            print(
                f'{len(old)} files have outdated headers.\n'
                f'    Pass --update to update.'
            )
        if missing:
            print(
                f'{len(missing)} files are missing headers.\n'
                '    Pass --add-missing to add copyright headers to '
                'these files.'
                f'    Auto detected header: {self.auto_header}'
            )

    def update(*root: ty.Iterable[Path]) -> None:
        """
        Updates existing copyright headers.
        :param root: Root paths
        :return: List[Path] of modified files.
        """

    def add_missing(*root: ty.Iterable[Path]) -> None:
        """
        Adds copyright headers where missing.
        :param root: Root paths
        :return: List[Path] of modified files.
        """

    # Accessors

    @property
    def outdated(self) -> ty.Set[Path]:
        """
        Gets files with outdated copyright headers.
        :return: List[Path]
        """
        if self._outdated is None:
            self._outdated = {
                path for path in self.files if
                TxtFile(path, self.copyright_re).header_is_outdated
            }
        return self._outdated

    @property
    def missing(self) -> ty.Set[Path]:
        """
        Finds files with missing copyright headers.
        :return: List[Path]
        """
        if self._missing is None:
            self._missing = {
                path for path in self.files
                if not TxtFile(path, self.copyright_re).copyright_str
            }
        return self._missing

    @property
    def auto_header(self) -> str:
        """
        Determines the auto-generated header to be added.
        :return: owner str.
        """


class FileType(ty.NamedTuple):
    """
    Class holding file type info.
    """
    name: str
    patterns: ty.Iterable[str]
    comment: str = ''
    block_pat: str = ''
    block_prefix: str = ''


class TxtFile:
    """
    Class handling a specific file's copyright header
    """
    def __init__(
            self, path: PathLike, copyright_re: str = COPYRIGHT_REGEX
    ) -> None:
        self.path = Path(path)
        self.copyright_re = copyright_re
        self.type = recognize(self.path)

        if not self.path.is_file():
            raise ValueError(f'Expected a file path. Got a dir: {self.path}')

    def update(self) -> None:
        """
        Updates the copyright header in a file.
        :return: None
        """
        updated_copyright = re.sub(
            pattern=YEAR_PATTERN,
            repl=f'{self.year_range.start}-{self.modification_year}',
            string=self.copyright_str,
            count=1
        )
        with self.path.open('r+') as f:
            new_content = re.sub(
                pattern=self.copyright_re,
                repl=updated_copyright,
                string=f.read(),
                count=1
            )
            f.seek(0)
            f.write(new_content)

    def add(self) -> None:
        """
        Adds a copyright header where one was previously missing.
        :return: None
        """

    @property
    def copyright_str(self) -> str:
        """
        Gets existing copyright string from a file.
        :return: Copyright str or empty string if not present.
        """
        with self.path.open() as f:
            match = re.search(self.copyright_re, f.read(1000))
            return match.group() if match is not None else ''

    @property
    def year_range(self) -> ty.Optional[range]:
        """
        Gets year range from copyright string.
        :return: Year range. range stop will be one greater than last
                    year in header, to allow easy inclusion testing.
        :raise ValueError if copyright string is missing or unable to
                    be parsed.
        """
        copyright_s = self.copyright_str
        if not copyright_s:
            raise ValueError('No copyright string found.')
        match = re.search(YEAR_PATTERN, copyright_s, flags=re.IGNORECASE)
        if not match:
            return None
        s = match.group()
        years = [int(y) for y in re.findall('[0-9]{4}', s)]
        if len(years) not in (1, 2):
            raise ValueError(
                f'Confusing header found: {repr(s)} in {self.path}'
            )
        return range(years[0], years[-1] + 1)

    @property
    def modification_year(self) -> int:
        """
        Gets the int representation of the year in which the file was
        last modified.
        :return: int
        """
        date_str = sub.check_output(
            args=(
                'git', 'log', '-1', '--format="%ad"', '--date=format:"%Y"',
                '--', f'{self.path.name}'
            ),
            cwd=self.path.parent,
            encoding='utf-8',
        ).strip('\'"\n')
        year = int(date_str)
        return year

    @property
    def header_is_outdated(self) -> bool:
        """
        Checks if the copyright string is outdated.
        :return: True if outdated.
        :raises: ValueError if header was not understood.
        """
        try:
            year_range = self.year_range
        except ValueError:
            # Copyright headers without a year are not
            # considered outdated.
            return False
        return self.modification_year >= year_range.stop

    @property
    def format(self) -> ty.Optional[str]:
        """
        Gets format of header (if found).

        :return: header format str (Ex: 'Copyright 2019 Bob') or None
        """
        try:
            return re.sub(
                pattern=YEAR_PATTERN,
                repl='{years}',
                string=self.copyright_str,
                count=1
            )
        except ValueError:
            return None

    def __repr__(self) -> str:
        return f'TxtFile[{self.path}]'


def recognize(path: Path) -> FileType:
    """
    Attempts to recognize a file's file type.
    :param path: Path to file to recognize.
    :return: FileType or None.
    """
    for t in file_types.values():
        for pat in t.patterns:
            if fnmatch.fnmatch(path.name, pat):
                return t


def fmt_file_list(paths: ty.Iterable[Path]) -> str:
    return '[\n    ' + '\n    '.join(str(path) for path in paths) + '\n]'


def main():
    """ Main entry point for copywriter. """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'path', nargs='*', default=['.'],
        help='root dir to search, or specific file.'
    )
    parser.add_argument(
        '--show', action='store_true',
        help='Display files that need changes.'
    )
    parser.add_argument(
        '--update', action='store_true',
        help='Update copyright notice years.'
    )
    parser.add_argument(
        '--add-missing', action='store_true',
        help='Add copyright notice where missing.'
    )
    parser.add_argument(
        '--copyright-re', default=COPYRIGHT_REGEX,
        help='Copyright header str.'
    )
    parser.add_argument(
        '--only-update', nargs='+', default='',
        help='Pattern to limit header updates to.'
    )
    args = parser.parse_args()

    copywriter = Copywriter(
        *args.path,
        copyright_re=args.copyright_re,
        update_re=args.only_update,
    )

    if args.show or not (args.update or args.add_missing):
        copywriter.show()
    if args.update:
        copywriter.update()
    if args.add_missing:
        copywriter.add_missing()


file_types = {f_type.name: f_type for f_type in (
    FileType(
        name='c-style',
        patterns=('*.c', '*.cc', '*.cpp', '*.cxx', '*.h', '*.hh', '*.hpp'),
        comment='//',
        block_pat=r'/\*.*\*/',
        block_prefix=' * ',
    ),
    FileType(
        name='py-style',
        patterns=('*.py', '*.pyi', '*.pyx', '*.pxd', '*.pyd', '*.pxi'),
        comment='#',
        block_pat=r'""".*"""',
        block_prefix='',
    ),
    FileType(
        name='cmake',
        patterns=('CMakeLists.txt', '*.cmake'),
        comment='#',
    ),
    FileType(
        name='bash',
        patterns=('*.sh', '*.bash'),
        comment='#',
    ),
)}


if __name__ == '__main__':
    main()
