import os
import tempfile
import subprocess
from git_restore_mtime import main, parse_args


def git_init(d):
    subprocess.check_call(["git", "init", d])
    subprocess.check_call(["git", "config", "user.email", "test@example.com"], cwd=d)
    subprocess.check_call(["git", "config", "user.name", "test test"], cwd=d)


def git_add(d, contents="", symlink=None, files=[]):
    for file in files:
        if symlink:
            os.symlink(symlink, f"{d}/{file}")
        elif contents:
            with open(f"{d}/{file}", 'w') as f:
                f.write(contents)
        subprocess.check_call(["git", "add", file], cwd=d)


def git_commit(d, date):
    subprocess.check_call(["git", "commit", "--allow-empty-message", "-m", "", "--date", date, "--no-edit"], cwd=d)


def git_switch(d, branch, create=False):
    cmd_list = ["git", "switch"]
    if create:
        cmd_list += ["-c", branch]
    else:
        cmd_list += [branch]

    subprocess.check_call(cmd_list, cwd=d)


def get_mtime_path(path):
    return os.stat(path).st_mtime


def test_main():
    with tempfile.TemporaryDirectory() as tmpdir:
        git_dir = f"{tmpdir}/git"

        git_init(git_dir)
        git_add(git_dir, "a", files=["file1", "file2", "☺"])
        git_commit(git_dir, date="1761123456 UTC")
        git_add(git_dir, "b", files=["file2"])
        git_commit(git_dir, date="1761123457 UTC")

        main(parse_args(("--cwd", git_dir)))

        assert get_mtime_path(f"{git_dir}/file1") == 1761123456.0
        assert get_mtime_path(f"{git_dir}/file2") == 1761123457.0


def test_skip_older_than():
    with tempfile.TemporaryDirectory() as tmpdir:
        git_dir = f"{tmpdir}/git"

        git_init(git_dir)
        git_add(git_dir, "a", files=["file1"])
        git_add(git_dir, symlink="file1", files=["file2"])
        git_commit(git_dir, date="1761123456 UTC")

        main(parse_args(("--cwd", git_dir, "--skip-older-than", "-1000000000")))

        assert get_mtime_path(f"{git_dir}/file1") != 1761123456.0

        main(parse_args(("--cwd", git_dir, "--skip-older-than", "1000000000")))

        assert get_mtime_path(f"{git_dir}/file1") == 1761123456.0


def test_unique_times():
    with tempfile.TemporaryDirectory() as tmpdir:
        git_dir = f"{tmpdir}/git"

        git_init(git_dir)
        git_add(git_dir, "a", files=["file1"])
        git_commit(git_dir, date="1761123456 UTC")

        main(parse_args(("--cwd", git_dir, "--unique-times")))

        assert get_mtime_path(f"{git_dir}/file1") == 1761123456.000001


def test_verbose():
    with tempfile.TemporaryDirectory() as tmpdir:
        git_dir = f"{tmpdir}/git"

        git_init(git_dir)
        git_add(git_dir, "a", files=["file1"])
        git_commit(git_dir, date="1761123456 UTC")

        main(parse_args(("--cwd", git_dir, "--verbose")))

        assert get_mtime_path(f"{git_dir}/file1") == 1761123456.0


def test_test():
    with tempfile.TemporaryDirectory() as tmpdir:
        git_dir = f"{tmpdir}/git"

        git_init(git_dir)
        git_add(git_dir, "a", files=["file1"])
        git_commit(git_dir, date="1761123456 UTC")

        main(parse_args(("--cwd", git_dir, "--test")))

        assert get_mtime_path(f"{git_dir}/file1") != 1761123456.0


def test_missing():
    with tempfile.TemporaryDirectory() as tmpdir:
        git_dir = f"{tmpdir}/git"

        git_init(git_dir)
        git_add(git_dir, "a", files=["file1"])
        git_commit(git_dir, date="1761123456 UTC")

        git_switch(git_dir, "branch1", True)

        git_add(git_dir, "b", files=["file2"])
        git_commit(git_dir, date="1761123457 UTC")

        git_switch(git_dir, "master")

        subprocess.check_call(["git", "merge", "--no-ff", "--no-commit", "branch1"], cwd=git_dir)

        git_add(git_dir, "b", files=["file3"])

        git_commit(git_dir, date="1761123458 UTC")

        main(parse_args(("--cwd", git_dir)))

        assert get_mtime_path(f"{git_dir}/file1") == 1761123456.0
        assert get_mtime_path(f"{git_dir}/file2") == 1761123457.0
        assert get_mtime_path(f"{git_dir}/file3") == 1761123458.0


def test_dirty():
    with tempfile.TemporaryDirectory() as tmpdir:
        git_dir = f"{tmpdir}/git"

        git_init(git_dir)
        git_add(git_dir, "a", files=["file1"])
        git_commit(git_dir, date="1761123456 UTC")

        with open(f'{git_dir}/file1', 'w') as f:
            f.write("dirty")

        subprocess.check_call(["git", "status", "--porcelain"], cwd=git_dir)

        main(parse_args(("--cwd", git_dir)))

        assert get_mtime_path(f"{git_dir}/file1") != 1761123456.0

def test_force():
    with tempfile.TemporaryDirectory() as tmpdir:
        git_dir = f"{tmpdir}/git"

        git_init(git_dir)
        git_add(git_dir, "a", files=["file1"])
        git_commit(git_dir, date="1761123456 UTC")

        with open(f'{git_dir}/file1', 'w') as f:
            f.write("dirty")

        subprocess.check_call(["git", "status", "--porcelain"], cwd=git_dir)

        main(parse_args(("--cwd", git_dir, "--force")))

        assert get_mtime_path(f"{git_dir}/file1") == 1761123456.0
