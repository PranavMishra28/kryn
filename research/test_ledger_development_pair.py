import unittest

from run_ledger_development_pair import permissions_digest


class PermissionNormalizationTest(unittest.TestCase):
    def test_only_generated_private_root_is_normalized(self):
        def permissions(workspace, private, effect="allow", generated="kryn-isolated-abc123"):
            return [
                {"action": "read", "resource": workspace + "/src/*", "effect": "allow"},
                {"action": "external_directory", "resource": private +
                 "/" + generated + "/xdg_data_home/opencode/shell/*/*", "effect": effect},
            ]

        a = permissions("/private/tmp/a/mount/workspace", "/private/tmp/a/mount/private",
                        generated="kryn-isolated-abc123_t")
        b = permissions("/private/tmp/b/mount/workspace", "/private/tmp/b/mount/private",
                        generated="kryn-isolated-xyz456")
        ah = permissions_digest(a, "/private/tmp/a/mount/workspace", "/private/tmp/a/mount/private")
        bh = permissions_digest(b, "/private/tmp/b/mount/workspace", "/private/tmp/b/mount/private")
        self.assertEqual(ah, bh)
        changed = permissions("/private/tmp/b/mount/workspace", "/private/tmp/b/mount/private", "deny")
        self.assertNotEqual(ah, permissions_digest(changed, "/private/tmp/b/mount/workspace",
                                                    "/private/tmp/b/mount/private"))
        self.assertIsNone(permissions_digest([{"action": "read", "resource": "*", "effect": "allow"}],
                                              "/private/tmp/a/mount/workspace", "/private/tmp/a/mount/private"))
        outside = b + [{"action": "external_directory", "effect": "allow",
                        "resource": "/other/kryn-isolated-abc123_t/secret/*"}]
        self.assertNotEqual(ah, permissions_digest(outside, "/private/tmp/b/mount/workspace",
                                                   "/private/tmp/b/mount/private"))


if __name__ == "__main__":
    unittest.main()
