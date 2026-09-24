"""Dependency-free tests for invitation token storage and symmetric friendships."""

import unittest

from app.core.social_tokens import canonical_friend_pair, hash_invite_code


class SocialTokenTests(unittest.TestCase):
    def test_invite_hash_is_deterministic_and_not_the_secret(self):
        secret = "high-entropy-invite-code"
        digest = hash_invite_code(secret)
        self.assertEqual(digest, hash_invite_code(secret))
        self.assertNotEqual(secret, digest)
        self.assertEqual(64, len(digest))

    def test_friendship_order_is_symmetric_and_stable(self):
        self.assertEqual(("alice", "bob"), canonical_friend_pair("alice", "bob"))
        self.assertEqual(("alice", "bob"), canonical_friend_pair("bob", "alice"))

    def test_friendship_rejects_missing_or_same_user(self):
        with self.assertRaises(ValueError):
            canonical_friend_pair("alice", "alice")
        with self.assertRaises(ValueError):
            canonical_friend_pair("", "bob")


if __name__ == "__main__":
    unittest.main()
