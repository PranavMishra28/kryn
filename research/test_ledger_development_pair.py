import unittest

from run_ledger_development_pair import permissions_digest


class PermissionNormalizationTest(unittest.TestCase):
    def test_only_generated_private_root_is_normalized(self):
        def permissions(workspace, private, effect="allow"):
            return [
                {"action": "read", "resource": workspace + "/src/*", "effect": "allow"},
                {"action": "external_directory", "resource": private +
                 "/kryn-isolated-abc123/xdg_data_home/opencode/shell/*/*", "effect": effect},
            ]

        a = permissions("/private/tmp/a/mount/workspace", "/private/tmp/a/mount/private")
        b = permissions("/private/tmp/b/mount/workspace", "/private/tmp/b/mount/private")
        ah = permissions_digest(a, "/private/tmp/a/mount/workspace", "/private/tmp/a/mount/private")
        bh = permissions_digest(b, "/private/tmp/b/mount/workspace", "/private/tmp/b/mount/private")
        self.assertEqual(ah, bh)
        changed = permissions("/private/tmp/b/mount/workspace", "/private/tmp/b/mount/private", "deny")
        self.assertNotEqual(ah, permissions_digest(changed, "/private/tmp/b/mount/workspace",
                                                    "/private/tmp/b/mount/private"))
        self.assertIsNone(permissions_digest([{"action": "read", "resource": "*", "effect": "allow"}],
                                              "/private/tmp/a/mount/workspace", "/private/tmp/a/mount/private"))


if __name__ == "__main__":
    unittest.main()
