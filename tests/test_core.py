import unittest

from watch.core import Watchers


def world():
    return Watchers(per_player_max=5, ttl_ms=100000, merge_ms=500)


class BasicTest(unittest.TestCase):
    def test_empty_pending(self):
        self.assertEqual(world().pending("p1", 0), [])

    def test_watch_then_pending(self):
        target = world()
        target.watch("p1", "l1", 0)
        self.assertEqual(target.pending("p1", 0), ["l1"])

    def test_change_without_watchers(self):
        self.assertEqual(world().change("l1", 0), [])

    def test_limits_are_stored(self):
        target = world()
        self.assertEqual((target.per_player_max, target.ttl_ms, target.merge_ms), (5, 100000, 500))

    def test_scanned_starts_at_zero(self):
        self.assertEqual(world().scanned_count(), 0)


if __name__ == "__main__":
    unittest.main()
