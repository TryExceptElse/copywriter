"""
Tests copywriter functionality.
"""
from pathlib import Path
import shutil
import tempfile
import textwrap

from freezegun import freeze_time

import copywriter


TEST_ROOT = Path(__file__).parent
TEST_RESOURCES = Path(TEST_ROOT, 'resources')
SAMPLE = Path(TEST_RESOURCES, 'sample')


def test_find_files():
    roots = [Path(SAMPLE, name) for name in (
        'cmake', 'include', 'scripts', 'src',
        'build.sh', 'CMakeLists.txt', 'readme.md'
    )]
    found = copywriter.Copywriter(*roots).files

    expected = {
        Path(SAMPLE, 'cmake', 'bar.cmake'),
        Path(SAMPLE, 'include', 'nested_dir', 'bar.h'),
        Path(SAMPLE, 'include', 'nested_dir', 'foo.h'),
        Path(SAMPLE, 'scripts', 'baz.py'),
        Path(SAMPLE, 'scripts', 'foo.py'),
        Path(SAMPLE, 'src', 'bar.c'),
        Path(SAMPLE, 'src', 'CMakeLists.txt'),
        Path(SAMPLE, 'src', 'foo.c'),
        Path(SAMPLE, 'build.sh'),
        Path(SAMPLE, 'CMakeLists.txt'),
    }

    assert found == expected


def test_copyright_header_is_found_in_cmake():
    txt = copywriter.TxtFile(Path(SAMPLE, 'CMakeLists.txt'))
    assert txt.copyright_str == 'Copyright 1085-1086 William'


def test_copyright_header_is_found_in_bash():
    txt = copywriter.TxtFile(Path(SAMPLE, 'build.sh'))
    assert txt.copyright_str == 'Copyright 1085-1086 William'


def test_copyright_header_is_found_in_py_docstring():
    txt = copywriter.TxtFile(Path(SAMPLE, 'scripts', 'baz.py'))
    assert txt.copyright_str == 'Copyright 1085 William'


def test_copyright_header_is_found_in_py_comment():
    txt = copywriter.TxtFile(Path(SAMPLE, 'scripts', 'foo.py'))
    assert txt.copyright_str == 'Copyright 1085 - 1086 William'


def test_copyright_header_is_found_in_c_block_comment():
    txt = copywriter.TxtFile(Path(SAMPLE, 'src', 'foo.c'))
    assert txt.copyright_str == 'Copyright 1085-1086 William'


def test_copyright_header_is_found_in_c_line_comment():
    txt = copywriter.TxtFile(Path(SAMPLE, 'src', 'bar.c'))
    assert txt.copyright_str == 'Copyright 1084-1085 William'


def test_missing_headers_are_found():
    roots = [Path(SAMPLE, name) for name in (
        'cmake', 'include', 'scripts', 'src',
        'build.sh', 'CMakeLists.txt', 'readme.md'
    )]
    found = copywriter.Copywriter(*roots).missing
    expected = {
        Path(SAMPLE, 'include', 'nested_dir', 'foo.h'),
        Path(SAMPLE, 'src', 'CMakeLists.txt'),
    }
    assert found == expected


@freeze_time("1086-01-14")
def test_outdated_headers_are_found():
    roots = [Path(SAMPLE, name) for name in (
        'cmake', 'include', 'scripts', 'src',
        'build.sh', 'CMakeLists.txt', 'readme.md'
    )]
    found = copywriter.Copywriter(*roots).outdated
    expected = {
        Path(SAMPLE, 'scripts', 'baz.py'),
        Path(SAMPLE, 'src', 'bar.c'),
    }
    assert found == expected


@freeze_time('1086-01-14')
def test_year_range_update():
    """ Tests that a copyright header's years are updated correctly """
    with tempfile.TemporaryDirectory() as tmp_dir:
        bar = Path(tmp_dir, 'bar.c')
        shutil.copy(src=Path(SAMPLE, 'src', 'bar.c'), dst=bar)
        copywriter.TxtFile(bar).update()
        with bar.open() as f:
            assert f.read() == '// Copyright 1084-1086 William\n'


@freeze_time('1086-01-14')
def test_single_year_update():
    """ Tests that a copyright header's years are updated correctly """
    with tempfile.TemporaryDirectory() as tmp_dir:
        baz = Path(tmp_dir, 'baz.py')
        shutil.copy(src=Path(SAMPLE, 'scripts', 'baz.py'), dst=baz)
        copywriter.TxtFile(baz).update()
        with baz.open() as f:
            assert 'Copyright 1085-1086 William' in f.read()


def test_c_header_addition():
    """ Tests addition of a copyright header to a C/C++ source file. """
    with tempfile.TemporaryDirectory() as tmp_dir:
        foo = Path(tmp_dir, 'foo.h')
        shutil.copy(
            src=Path(SAMPLE, 'include', 'nested_dir', 'foo.h'), dst=foo
        )
        expected = textwrap.dedent("""
        /**
         * 
         *
         * Unrelated header
         */
        """)
        copywriter.TxtFile(foo).add()
        with foo.open() as f:
            assert ''
