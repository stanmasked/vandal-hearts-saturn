"""Stage150 ROM-free synthetic tests for the private durable-storage gate."""
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
import unittest

from tools import saturn_private_stage150_storage_guard as guard

GIB = 1024 * 1024 * 1024


def fixture(root):
    workspace = root / "private"
    workspace.mkdir(mode=0o700)
    source = workspace / "disc-private-file.bin"
    source.write_bytes(b"synthetic fixture, not a ROM")
    source.chmod(0o600)
    output = root / "captures"
    output.mkdir(mode=0o700)
    return output, source


class Stage150PrivateStorageGateTests(unittest.TestCase):
    def test_linux_overlay_capture_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            output, source = fixture(Path(td))
            def fake_fs(path, system):
                return "overlay" if path == output else "ext4"
            with patch.dict(os.environ, {}, clear=True), \
                 patch.object(guard.platform, "system", return_value="Linux"), \
                 patch.object(guard, "_storage_type", side_effect=fake_fs):
                with self.assertRaisesRegex(ValueError, "volatile, network"):
                    guard.assert_durable_private_workspace(output, (source,))

    def test_linux_tmpfs_source_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            output, source = fixture(Path(td))
            def fake_fs(path, system):
                return "tmpfs" if path == source else "ext4"
            with patch.dict(os.environ, {}, clear=True), \
                 patch.object(guard.platform, "system", return_value="Linux"), \
                 patch.object(guard, "_storage_type", side_effect=fake_fs):
                with self.assertRaisesRegex(ValueError, "volatile, network"):
                    guard.assert_durable_private_workspace(output, (source,))

    def test_ci_environment_rejected_before_source_read(self):
        with tempfile.TemporaryDirectory() as td:
            output, source = fixture(Path(td))
            for key in ("CI", "GITHUB_ACTIONS", "CIRCLECI"):
                with self.subTest(key=key), patch.dict(os.environ, {key: "true"}, clear=True):
                    with self.assertRaisesRegex(ValueError, "CI-hosted"):
                        guard.assert_durable_private_workspace(output, (source,))

    def test_successful_persistent_ext4_preflight_not_claiming_drive_readback(self):
        with tempfile.TemporaryDirectory() as td:
            output, source = fixture(Path(td))
            with patch.dict(os.environ, {}, clear=True), \
                 patch.object(guard.platform, "system", return_value="Linux"), \
                 patch.object(guard, "_storage_type", return_value="ext4"), \
                 patch.object(guard.shutil, "disk_usage",
                              return_value=SimpleNamespace(free=8 * GIB)):
                r = guard.assert_durable_private_workspace(output, (source,))
            self.assertEqual(r["filesystem_types"], ["ext4"])
            self.assertTrue(r["capture_and_source_volumes_accepted"])
            self.assertFalse(r["drive_upload_and_independent_readback_verified"])
            self.assertFalse(r["persistent_storage_survives_power_failure_independently_verified"])

    def test_low_free_space_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            output, source = fixture(Path(td))
            with patch.dict(os.environ, {}, clear=True), \
                 patch.object(guard.platform, "system", return_value="Linux"), \
                 patch.object(guard, "_storage_type", return_value="ext4"), \
                 patch.object(guard.shutil, "disk_usage",
                              return_value=SimpleNamespace(free=guard.MIN_FREE_BYTES - 1)):
                with self.assertRaisesRegex(ValueError, "insufficient free space"):
                    guard.assert_durable_private_workspace(output, (source,))

    def test_world_readable_media_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            output, source = fixture(Path(td))
            source.chmod(0o644)
            with patch.dict(os.environ, {}, clear=True), \
                 patch.object(guard.platform, "system", return_value="Linux"), \
                 patch.object(guard, "_storage_type", return_value="ext4"):
                with self.assertRaisesRegex(ValueError, "permissions"):
                    guard.assert_durable_private_workspace(output, (source,))

    def test_symlinked_ancestor_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            output, source = fixture(Path(td))
            alias = Path(td) / "alias"
            alias.symlink_to(Path(td) / "private", target_is_directory=True)
            with patch.dict(os.environ, {}, clear=True), \
                 patch.object(guard.platform, "system", return_value="Linux"), \
                 patch.object(guard, "_storage_type", return_value="ext4"):
                with self.assertRaisesRegex(ValueError, "ancestor contains symlink"):
                    guard.assert_durable_private_workspace(output, (alias / source.name,))

    def test_linux_mountinfo_prefers_longest_matching_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td).resolve()
            fakes = ((Path("/"), "overlay"), (path, "ext4"),
                     (Path(str(path) + "2"), "tmpfs"))
            self.assertEqual(guard._linux_type_for_path(path, fakes), "ext4")
            self.assertEqual(guard._linux_type_for_path(Path("/"), fakes), "overlay")

    def test_mountinfo_parses_octal_escaped_paths(self):
        raw = ("23 12 1:2 / / rw,relatime - overlay overlay rw\n"
               "24 23 1:3 / /Volumes/Private\\040Saturn rw - ext4 /dev/vda2 rw\n")
        mounts = guard._parse_linux_mountinfo(raw)
        self.assertIn((Path("/Volumes/Private Saturn"), "ext4"), mounts)
        with self.assertRaisesRegex(ValueError, "unknown escape"):
            guard._parse_linux_mountinfo("24 23 1:3 / /a\\999 rw - ext4 /dev/vda rw\n")

    def test_native_macos_apfs_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            output, source = fixture(Path(td))
            with patch.dict(os.environ, {}, clear=True), \
                 patch.object(guard.platform, "system", return_value="Darwin"), \
                 patch.object(guard, "_storage_type", return_value="apfs"), \
                 patch.object(guard.shutil, "disk_usage",
                              return_value=SimpleNamespace(free=8 * GIB)):
                r = guard.assert_durable_private_workspace(output, (source,))
            self.assertEqual(r["native_host_class"], "Darwin")


if __name__ == "__main__":
    unittest.main()
