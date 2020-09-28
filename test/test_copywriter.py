"""
Tests copywriter functionality.
"""
from pathlib import Path
import shutil
import tempfile
import textwrap

import copywriter


TEST_ROOT = Path(__file__).parent
TEST_RESOURCES = Path(TEST_ROOT, 'resources')
SAMPLE = Path(TEST_RESOURCES, 'sample')
ROOT = TEST_ROOT.parent


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
    assert txt.copyright_str == 'Copyright 2019-2020 Bob'


def test_copyright_header_is_found_in_bash():
    txt = copywriter.TxtFile(Path(SAMPLE, 'build.sh'))
    assert txt.copyright_str == 'Copyright 2019-2020 Bob'


def test_copyright_header_is_found_in_py_docstring():
    txt = copywriter.TxtFile(Path(SAMPLE, 'scripts', 'baz.py'))
    assert txt.copyright_str == 'Copyright 2019 Bob'


def test_copyright_header_is_found_in_py_comment():
    txt = copywriter.TxtFile(Path(SAMPLE, 'scripts', 'foo.py'))
    assert txt.copyright_str == 'Copyright 2019 - 2020 Bob'


def test_copyright_header_is_found_in_c_block_comment():
    txt = copywriter.TxtFile(Path(SAMPLE, 'src', 'foo.c'))
    assert txt.copyright_str == 'Copyright 2019-2020 Bob'


def test_copyright_header_is_found_in_c_line_comment():
    txt = copywriter.TxtFile(Path(SAMPLE, 'src', 'bar.c'))
    assert txt.copyright_str == 'Copyright 2018-2019 Bob'


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


def test_year_range_update():
    """ Tests that a copyright header's years are updated correctly """
    with tempfile.TemporaryDirectory() as tmp_dir:
        shutil.copytree(src=ROOT, dst=Path(tmp_dir, 'sample'))
        bar = Path(tmp_dir, 'sample/test/resources/sample/src/bar.c')
        copywriter.TxtFile(bar).update()
        with bar.open() as f:
            assert f.read() == '// Copyright 2018-2020 Bob\n'


def test_single_year_update():
    """ Tests that a copyright header's years are updated correctly """
    with tempfile.TemporaryDirectory() as tmp_dir:
        shutil.copytree(src=ROOT, dst=Path(tmp_dir, 'sample'))
        baz = Path(tmp_dir, 'sample/test/resources/sample/scripts/baz.py')
        copywriter.TxtFile(baz).update()
        with baz.open() as f:
            assert 'Copyright 2019-2020 Bob' in f.read()


def test_format_detection():
    fmt = copywriter.TxtFile(Path(SAMPLE, 'scripts/baz.py')).format
    assert 'Copyright {years} Bob' == fmt


def test_auto_header():
    roots = [Path(SAMPLE, name) for name in (
        'cmake', 'include', 'scripts', 'src',
        'build.sh', 'CMakeLists.txt', 'readme.md'
    )]
    auto_header = copywriter.Copywriter(*roots).auto_header
    assert auto_header == 'Copyright {years} Bob'


def test_c_header_addition(tmp_path: Path):
    """ Tests addition of a copyright header to a C/C++ source file. """
    shutil.copytree(src=ROOT, dst=Path(tmp_path, 'sample'))
    foo = Path(
        tmp_path, 'sample/test/resources/sample/include/nested_dir/foo.h'
    )
    shutil.copy(src=foo, dst=Path(tmp_path, 'sample'))
    expected = textwrap.dedent("""
    /**
     * Copyright 2020 Monty
     * 
     * Unrelated header
     */
    """[1:])  # skip opening newline.
    copywriter.TxtFile(foo).add('Copyright {year} Monty')
    with foo.open() as f:
        assert f.read() == expected
