"""Dependency-free tests for invitation token storage and symmetric friendships."""

import unittest

from app.core.social_tokens import (
    can_add_team_member,
    can_change_team_role,
    can_remove_team_member,
    canonical_friend_pair,
    hash_invite_code,
    shared_quest_reward_key,
)


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

    def test_only_owner_or_admin_can_add_regular_members(self):
        self.assertTrue(can_add_team_member("owner", "member"))
        self.assertTrue(can_add_team_member("admin", "member"))
        self.assertFalse(can_add_team_member("member", "member"))
        self.assertFalse(can_add_team_member("admin", "admin"))

    def test_only_owner_can_change_non_owner_roles(self):
        self.assertTrue(can_change_team_role("owner", "member", "admin"))
        self.assertFalse(can_change_team_role("admin", "member", "admin"))
        self.assertFalse(can_change_team_role("owner", "owner", "member"))
        self.assertFalse(can_change_team_role("owner", "member", "owner"))

    def test_member_removal_preserves_owner_and_admin_boundaries(self):
        self.assertTrue(can_remove_team_member("member", "member", True))
        self.assertFalse(can_remove_team_member("owner", "owner", True))
        self.assertTrue(can_remove_team_member("owner", "admin", False))
        self.assertFalse(can_remove_team_member("admin", "admin", False))
        self.assertTrue(can_remove_team_member("admin", "member", False))

    def test_shared_reward_key_is_stable_and_namespaced(self):
        key = shared_quest_reward_key("moscow-red-square")
        self.assertEqual(key, shared_quest_reward_key("moscow-red-square"))
        self.assertEqual("team-quest:moscow-red-square", key)
        with self.assertRaises(ValueError):
            shared_quest_reward_key("")


if __name__ == "__main__":
    unittest.main()
