import multiprocessing
from importlib.util import spec_from_loader, module_from_spec
from importlib.machinery import SourceFileLoader
import sys
import os
import tempfile
import shutil
import subprocess


def get_git_restore_mtime(tmpdir, *args):
    sys.argv = args
    spec = spec_from_loader("__main__", SourceFileLoader("__main__", "git-restore-mtime"))
    git_restore_mtime = module_from_spec(spec)
    spec.loader.exec_module(git_restore_mtime)


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


def git_merge(d, branch):
    subprocess.check_call(["git", "merge", "--no-ff", branch, "--no-edit", "-s", "ours"], cwd=d)


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

        p = multiprocessing.Process(target=get_git_restore_mtime, args=(tmpdir, "", "--cwd", git_dir))
        p.start()
        p.join()

        assert get_mtime_path(f"{git_dir}/file1") == 1761123456.0
        assert get_mtime_path(f"{git_dir}/file2") == 1761123457.0


def test_skip_older_than():
    with tempfile.TemporaryDirectory() as tmpdir:
        git_dir = f"{tmpdir}/git"

        git_init(git_dir)
        git_add(git_dir, "a", files=["file1"])
        git_add(git_dir, symlink="file1", files=["file2"])
        git_commit(git_dir, date="1761123456 UTC")

        p = multiprocessing.Process(target=get_git_restore_mtime, args=(tmpdir, "", "--cwd", git_dir, "--skip-older-than", "-1000000000"))
        p.start()
        p.join()

        assert get_mtime_path(f"{git_dir}/file1") != 1761123456.0

        p = multiprocessing.Process(target=get_git_restore_mtime, args=(tmpdir, "", "--cwd", git_dir, "--skip-older-than", "1000000000"))
        p.start()
        p.join()

        assert get_mtime_path(f"{git_dir}/file1") == 1761123456.0


def test_unique_times():
    with tempfile.TemporaryDirectory() as tmpdir:
        git_dir = f"{tmpdir}/git"

        git_init(git_dir)
        git_add(git_dir, "a", files=["file1"])
        git_commit(git_dir, date="1761123456 UTC")

        p = multiprocessing.Process(target=get_git_restore_mtime, args=(tmpdir, "", "--cwd", git_dir, "--unique-times"))
        p.start()
        p.join()

        assert get_mtime_path(f"{git_dir}/file1") == 1761123456.000001


def test_verbose():
    with tempfile.TemporaryDirectory() as tmpdir:
        git_dir = f"{tmpdir}/git"

        git_init(git_dir)
        git_add(git_dir, "a", files=["file1"])
        git_commit(git_dir, date="1761123456 UTC")

        p = multiprocessing.Process(target=get_git_restore_mtime, args=(tmpdir, "", "--cwd", git_dir, "--verbose"))
        p.start()
        p.join()

        assert get_mtime_path(f"{git_dir}/file1") == 1761123456.0


def test_test():
    with tempfile.TemporaryDirectory() as tmpdir:
        git_dir = f"{tmpdir}/git"

        git_init(git_dir)
        git_add(git_dir, "a", files=["file1"])
        git_commit(git_dir, date="1761123456 UTC")

        p = multiprocessing.Process(target=get_git_restore_mtime, args=(tmpdir, "", "--cwd", git_dir, "--test"))
        p.start()
        p.join()

        assert get_mtime_path(f"{git_dir}/file1") != 1761123456.0


def test_missing():
    with tempfile.TemporaryDirectory() as tmpdir:
        git_dir = f"{tmpdir}/git"

        git_init(git_dir)
        git_add(git_dir, "a", files=["file1"])
        git_commit(git_dir, date="1761123456 UTC")

        git_switch(git_dir, "branch1", True)

        git_add(git_dir, "a", files=["file2"])
        git_commit(git_dir, date="1761123456 UTC")

        git_switch(git_dir, "master")

        git_switch(git_dir, "branch2", True)

        git_add(git_dir, "b", files=["file2"])
        git_commit(git_dir, date="1761123456 UTC")

        git_switch(git_dir, "branch1")

        git_merge(git_dir, "branch2")

        git_switch(git_dir, "master")

        git_merge(git_dir, "branch1")

        subprocess.check_call(["git", "log", "--graph", "--raw", "--no-show-signature"], cwd=git_dir)

        p = multiprocessing.Process(target=get_git_restore_mtime, args=(tmpdir, "", "--cwd", git_dir, "--merge"))
        p.start()
        p.join()

        assert get_mtime_path(f"{git_dir}/file1") == 1761123456.0
