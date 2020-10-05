"""
Tests copywriter functionality.
"""
import glob
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


def test_year_range_update(tmp_path):
    """ Tests that a copyright header's years are updated correctly """
    shutil.copytree(src=ROOT, dst=Path(tmp_path, 'sample'))
    bar = Path(tmp_path, 'sample/test/resources/sample/src/bar.c')
    copywriter.TxtFile(bar).update()
    with bar.open() as f:
        assert f.read() == '// Copyright 2018-2020 Bob\n'


def test_single_year_update(tmp_path):
    """ Tests that a copyright header's years are updated correctly """
    shutil.copytree(src=ROOT, dst=Path(tmp_path, 'sample'))
    baz = Path(tmp_path, 'sample/test/resources/sample/scripts/baz.py')
    copywriter.TxtFile(baz).update()
    with baz.open() as f:
        assert 'Copyright 2019-2020 Bob' in f.read()


def test_format_detection():
    fmt = copywriter.TxtFile(Path(SAMPLE, 'scripts/baz.py')).format
    assert 'Copyright {year} Bob' == fmt


def test_auto_header():
    roots = [Path(SAMPLE, name) for name in (
        'cmake', 'include', 'scripts', 'src',
        'build.sh', 'CMakeLists.txt', 'readme.md'
    )]
    auto_header = copywriter.Copywriter(*roots).auto_header
    assert auto_header == 'Copyright {year} Bob'


def test_c_header_expansion(tmp_path: Path):
    """ Tests expansion of a copyright header to a C/C++ source file. """
    path = _get_test_file(tmp_path, 'missing/existing_doc/c.h')
    expected = textwrap.dedent("""
    /**
     * Copyright 2020 Monty
     * 
     * Documentation text
     */
    
    /**
     * @brief Adds A to B.
     */
    int foo(int a, int b) {
        return a + b;
    }
    """[1:])  # skip opening newline.
    copywriter.TxtFile(path).add('Copyright {year} Monty')
    with path.open() as f:
        assert f.read() == expected


def test_bash_expansion(tmp_path: Path):
    """ Tests expansion of a copyright header to a bash file. """
    path = _get_test_file(tmp_path, 'missing/existing_doc/bash.sh')
    expected = textwrap.dedent("""
    #
    # Copyright 2020 Monty
    #
    # Some documentation
    
    echo "foo"
    """[1:])  # skip opening newline.
    copywriter.TxtFile(path).add('Copyright {year} Monty')
    with path.open() as f:
        assert f.read() == expected


def test_bash_with_shebang_expansion(tmp_path: Path):
    """ Tests expansion of a copyright header to a bash file. """
    path = _get_test_file(
        tmp_path, 'missing/existing_doc/bash_with_shebang.sh'
    )
    expected = textwrap.dedent("""
    #!/usr/bin/bash
    #
    # Copyright 2020 Monty
    #
    # Some documentation
    
    echo "foo"
    """[1:])  # skip opening newline.
    copywriter.TxtFile(path).add('Copyright {year} Monty')
    with path.open() as f:
        assert f.read() == expected


def test_cmake_expansion(tmp_path: Path):
    """ Tests expansion of a copyright header to a cmake file. """
    path = _get_test_file(tmp_path, 'missing/existing_doc/cmake.cmake')
    expected = textwrap.dedent("""
    #
    # Copyright 2020 Monty
    #
    # CMake file that does stuff.
    #
    
    
    message(STATUS "Doing the thing.")
    """[1:])  # skip opening newline.
    copywriter.TxtFile(path).add('Copyright {year} Monty')
    with path.open() as f:
        assert f.read() == expected


def test_py_expansion(tmp_path: Path):
    """ Tests expansion of a copyright header to a cmake file. """
    path = _get_test_file(tmp_path, 'missing/existing_doc/py.py')
    expected = textwrap.dedent("""
    \"\"\"
    Copyright 2020 Monty
    
    Python file containing documentation.
    \"\"\"
    
    
    def foo(a, b):
        \"\"\"
        Adds a to b.
        \"\"\"
        return a + b
    """[1:])  # skip opening newline.
    copywriter.TxtFile(path).add('Copyright {year} Monty')
    with path.open() as f:
        content = f.read()
    assert content == expected


def test_py_with_shebang_expansion(tmp_path: Path):
    """ Tests expansion of a copyright header to a cmake file. """
    path = _get_test_file(tmp_path, 'missing/existing_doc/py_with_shebang.py')
    expected = textwrap.dedent("""
    #!/usr/bin/env/python3
    \"\"\"
    Copyright 2020 Monty

    Python file containing documentation.
    \"\"\"


    def foo(a, b):
        \"\"\"
        Adds a to b.
        \"\"\"
        return a + b
    """[1:])  # skip opening newline.
    copywriter.TxtFile(path).add('Copyright {year} Monty')
    with path.open() as f:
        content = f.read()
    assert content == expected


def test_c_header_addition(tmp_path: Path):
    """ Tests addition of a copyright header to a C/C++ source file. """
    path = _get_test_file(tmp_path, 'missing/no_doc/c.h')
    expected = textwrap.dedent("""
    /*
     * Copyright 2020 Monty
     */
    #include <stdio.h>
    
    
    /**
     * @brief Adds A to B.
     */
    int foo(int a, int b) {
        return a + b;
    }
    """[1:])  # skip opening newline.
    copywriter.TxtFile(path).add('Copyright {year} Monty')
    with path.open() as f:
        assert f.read() == expected


def test_bash_addition(tmp_path: Path):
    """ Tests addition of a copyright header to a bash file. """
    path = _get_test_file(tmp_path, 'missing/no_doc/bash.sh')
    expected = textwrap.dedent("""
    #
    # Copyright 2020 Monty
    #
    echo "foo"
    """[1:])  # skip opening newline.
    copywriter.TxtFile(path).add('Copyright {year} Monty')
    with path.open() as f:
        assert f.read() == expected


def test_bash_with_shebang_addition(tmp_path: Path):
    """ Tests addition of a copyright header to a bash file. """
    path = _get_test_file(tmp_path, 'missing/no_doc/bash_with_shebang.sh')

    expected = textwrap.dedent("""
    #!/usr/bin/bash
    #
    # Copyright 2020 Monty
    #
    
    echo "foo"
    """[1:])  # skip opening newline.
    copywriter.TxtFile(path).add('Copyright {year} Monty')
    with path.open() as f:
        assert f.read() == expected


def test_cmake_addition(tmp_path: Path):
    """ Tests addition of a copyright header to a cmake file. """
    path = _get_test_file(tmp_path, 'missing/no_doc/cmake.cmake')
    expected = textwrap.dedent("""
    #
    # Copyright 2020 Monty
    #
    
    message(STATUS "Doing the thing.")
    """[1:])  # skip opening newline.
    copywriter.TxtFile(path).add('Copyright {year} Monty')
    with path.open() as f:
        assert f.read() == expected


def test_py_addition(tmp_path: Path):
    """ Tests addition of a copyright header to a cmake file. """
    path = _get_test_file(tmp_path, 'missing/no_doc/py.py')
    expected = textwrap.dedent("""
    \"\"\"
    Copyright 2020 Monty
    \"\"\"
    
    
    def foo(a, b):
        \"\"\"
        Adds a to b.
        \"\"\"
        return a + b
    """[1:])  # skip opening newline.
    copywriter.TxtFile(path).add('Copyright {year} Monty')
    with path.open() as f:
        content = f.read()
    assert content == expected


def test_py_with_shebang_addition(tmp_path: Path):
    """ Tests addition of a copyright header to a cmake file. """
    path = _get_test_file(tmp_path, 'missing/no_doc/py_with_shebang.py')
    expected = textwrap.dedent("""
    #!/usr/bin/env/python3
    \"\"\"
    Copyright 2020 Monty
    \"\"\"


    def foo(a, b):
        \"\"\"
        Adds a to b.
        \"\"\"
        return a + b
    """[1:])  # skip opening newline.
    copywriter.TxtFile(path).add('Copyright {year} Monty')
    with path.open() as f:
        content = f.read()
    assert content == expected


def test_show_succeeds(tmp_path):
    test_source_path = Path(tmp_path, 'test_sources')
    shutil.copytree(src=ROOT, dst=test_source_path)
    writer = copywriter.Copywriter(test_source_path)


def test_update_succeeds(tmp_path):
    test_source_path = Path(tmp_path, 'test_sources')
    shutil.copytree(src=ROOT, dst=test_source_path)
    copywriter.Copywriter(test_source_path).update()


def test_add_succeeds(tmp_path):
    test_source_path = Path(tmp_path, 'test_sources')
    shutil.copytree(src=ROOT, dst=test_source_path)
    copywriter.Copywriter(test_source_path).add_missing()


# Test util.


def _get_test_file(tmp_dir: Path, resource: str) -> Path:
    """
    Copies source to tmp dir and returns path to the moved file.

    The complete repo is copied to preserve git info which is
    needed by copywriter.
    """
    test_source_path = Path(tmp_dir, 'test_sources')
    shutil.copytree(src=ROOT, dst=test_source_path)
    relative_path = Path(TEST_RESOURCES, resource).relative_to(ROOT)
    copied_path = Path(test_source_path, relative_path)
    return copied_path
