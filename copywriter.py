#!/usr/bin/env/python3
"""
Utility for adding and updating copyright notices on files.
"""
import argparse
import collections
import fnmatch
import glob
import os
from pathlib import Path
import itertools
import re
import string
import subprocess as sub
import sys
import typing as ty


YEAR_PATTERN = '[0-9]{4}( *-? *[0-9]{4})?'
COPYRIGHT_REGEX = 'Copyright .*'


PathLike = ty.Union[str, os.PathLike, Path]


class Copywriter:
    """
    Class handling copywriter operation.

    Takes parameters which define how copyright notices are found and
    formatted, and provides functions for updating existing copyright
    notices where they have become out of date, or adding new notices
    where they are missing.
    """
    def __init__(
            self,
            *root: PathLike,
            copyright_re: str = COPYRIGHT_REGEX,
            filter_re: str = '',
            fmt: str = '',
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
        self.filter_re = filter_re

        self.files = self._find_files(*self.roots)
        self._outdated: ty.Optional[ty.Set[Path]] = None
        self._missing: ty.Optional[ty.Set[Path]] = None
        self._passed_fmt = fmt
        self._auto_format = ''

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

        def is_git_tracked(path: Path) -> bool:
            return sub.run(
                args=('git', 'ls-files', '--error-unmatch', path.absolute()),
                stderr=sub.DEVNULL,
                stdout=sub.DEVNULL,
                cwd=path.parent
            ).returncode == 0

        return {path for path in paths if is_git_tracked(path)}

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
            )
            if self._passed_fmt:
                print(f'    Passed header: {self._passed_fmt}')
            else:
                print(f'    Auto detected header: {self.auto_header}')

    def update(self) -> None:
        """
        Updates existing copyright headers.

        :return: List[Path] of modified files.
        """
        for path in self.outdated:
            TxtFile(path, self.copyright_re).update()

    def add_missing(self, header: str = '') -> None:
        """
        Adds copyright headers where missing.

        :param header: Copyright header format. Defaults to auto_header.
        :return: List[Path] of modified files.
        """
        header = header or self.auto_header
        for path in self.missing:
            TxtFile(path, self.copyright_re).add(header)

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
    def format(self) -> str:
        """
        Gets format which will be used for added copyright notices.
        """
        return self._passed_fmt or self.auto_header

    @property
    def auto_header(self) -> str:
        """
        Determines the auto-generated header to be added.
        :return: owner str.
        """
        if not self._auto_format:
            formats = [TxtFile(path).format for path in self.files]
            filtered = filter(None, formats)
            counter = collections.Counter(filtered)
            self._auto_format = counter.most_common(n=1)[0][0]
        return self._auto_format


class FileType(ty.NamedTuple):
    """
    Class holding file type info.
    """
    name: str
    patterns: ty.Iterable[str]
    comment: str = ''
    block_start: str = ''
    block_end: str = ''
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

        if not self.type:
            raise ValueError(f'Could not recognize file type: {self.path}')

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

    def add(self, fmt: str) -> None:
        """
        Adds a copyright header where one was previously missing.
        :return: None
        """
        notice = fmt.format(year=self.modification_year)
        with self.path.open('r+') as f:
            lines = f.readlines()
            if self.type.block_start:
                self._add_block_notice(lines, notice)
            else:
                self._add_comment_notice(lines, notice)

            # Write modified lines to file.
            f.seek(0)
            f.writelines(lines)

    def _add_comment_notice(self, lines: ty.List[str], notice: str) -> None:
        """
        Adds a copyright notice using commented lines (Ex: '// ...').
        """
        # Add copyright header in comment
        if lines and lines[0].startswith('#!'):
            insert_i = 1
        else:
            insert_i = 0
        new_text = (
                f'{self.type.comment}\n' +
                f'{self.type.comment} {notice}\n' +
                f'{self.type.comment}\n'
        )
        lines.insert(insert_i, new_text)

    def _add_block_notice(self, lines: ty.List[str], notice: str) -> None:
        """
        Adds a copyright notice using comment block ('/** ... */')
        """
        if self.type.block_start:
            block_start = self.type.block_start
        else:
            block_start = self.type.comment

        def find_block_start(lines_: ty.Sequence[str]) -> int:
            """
            Finds line index of block start, raises ValueError if
            not found.
            :return: int index of block start line.
            """
            for i, line in enumerate(lines_):
                if line.startswith(block_start):
                    return i
            raise ValueError('No block start found in passed lines.')

        def create_new_block():
            if lines and lines[0].startswith('#!'):
                insert_i = 1
            else:
                insert_i = 0
            new_text = (
                    f'{self.type.block_start}\n' +
                    f'{self.type.block_prefix}{notice}\n' +
                    f'{self.type.block_end}\n'
            )
            lines.insert(insert_i, new_text)

        def expand_existing_block(block_i_):
            original = opening_lines[block_i_]
            split_i = original.find(block_start) + len(block_start)

            # Leave characters attached to the block start
            # in place.
            while original[split_i] not in string.whitespace:
                split_i += 1

            new = (
                    original[:split_i].rstrip() +
                    f'\n{self.type.block_prefix}{notice}\n' +
                    f'{self.type.block_prefix}' +
                    original[split_i:]
            )
            lines[block_i_] = new

        opening_lines = lines[:3]

        # Check if there is an existing header to expand.
        try:
            block_i = find_block_start(opening_lines)
        except ValueError:
            create_new_block()
        else:
            expand_existing_block(block_i)

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
                    Return value will be `None` if copyright string has
                    no year.
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
        try:
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
        except Exception as ex:
            raise ValueError(
                f'Failed to get modification year for {self.path.name}'
            ) from ex

    @property
    def header_is_outdated(self) -> bool:
        """
        Checks if the copyright string is outdated.
        :return: True if outdated, False otherwise.
        :raises: ValueError if header was not understood.
        """
        try:
            year_range = self.year_range
        except ValueError:
            # Copyright headers without a year are not
            # considered outdated.
            return False
        if year_range is None:
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
                repl='{year}',
                string=self.copyright_str,
                count=1
            )
        except ValueError:
            return None

    def __repr__(self) -> str:
        return f'TxtFile[{self.path}]'


def recognize(path: Path) -> FileType:
    """
    Attempts to recognize a file's type.
    :param path: Path to file to recognize.
    :return: FileType or None.
    """
    for t in file_types.values():
        for pat in t.patterns:
            if fnmatch.fnmatch(path.name, pat):
                return t


def fmt_file_list(paths: ty.Iterable[Path]) -> str:
    """
    Produces reader-friendly list representation from elements.
    """
    return '[\n    ' + '\n    '.join(str(path) for path in paths) + '\n]'


def main():
    """ Main entry point for copywriter. """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'path', nargs='*', default=['.'],
        help='root dir to search, or specific file.'
    )
    parser.add_argument(
        '--show', '-S', action='store_true',
        help='Display files that need changes.'
    )
    parser.add_argument(
        '--update', '-U', action='store_true',
        help='Update copyright notice years.'
    )
    parser.add_argument(
        '--add-missing', '-A', action='store_true',
        help='Add copyright notice where missing.'
    )
    parser.add_argument(
        '--format', '--fmt', '-f',
        help='Format used for copyright notice.'
    )
    parser.add_argument(
        '--copyright-re', default=COPYRIGHT_REGEX,
        help='Copyright header str.'
    )
    parser.add_argument(
        '--filter-re', nargs='+', default='',
        help='Pattern to limit header changes to.'
    )
    args = parser.parse_args()

    copywriter = Copywriter(
        *args.path,
        fmt=args.format,
        copyright_re=args.copyright_re,
        filter_re=args.filter_re,
    )
    if not copywriter.files:
        print(
            'No files tracked by git were found using passed parameters.',
            file=sys.stderr
        )
        return -1

    if args.show or not (args.update or args.add_missing):
        copywriter.show()
    if args.update:
        copywriter.update()
    if args.add_missing:
        copywriter.add_missing()

    return 0


file_types = {f_type.name: f_type for f_type in (
    FileType(
        name='c-style',
        patterns=('*.c', '*.cc', '*.cpp', '*.cxx', '*.h', '*.hh', '*.hpp'),
        comment='//',
        block_start='/*',
        block_end=' */',
        block_prefix=' * ',
    ),
    FileType(
        name='py-style',
        patterns=('*.py', '*.pyi', '*.pyx', '*.pxd', '*.pyd', '*.pxi'),
        comment='#',
        block_start='"""',
        block_end='"""',
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
    exit(main())
