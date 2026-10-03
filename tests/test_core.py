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


class CapTest(unittest.TestCase):
    def test_over_cap_evicts_earliest(self):
        target = Watchers(per_player_max=2, ttl_ms=100000, merge_ms=0)
        target.watch("p1", "l0", 0)
        target.watch("p1", "l1", 1)
        target.watch("p1", "l2", 2)
        self.assertEqual(target.pending("p1", 3), ["l1", "l2"])

    def test_pending_never_exceeds_cap(self):
        target = Watchers(per_player_max=3, ttl_ms=100000, merge_ms=0)
        for index in range(10):
            target.watch("p1", "l%d" % index, index)
            self.assertLessEqual(len(target.pending("p1", index)), 3)

    def test_cap_is_per_player(self):
        target = Watchers(per_player_max=1, ttl_ms=100000, merge_ms=0)
        target.watch("p1", "l1", 0)
        target.watch("p2", "l2", 0)
        target.watch("p2", "l3", 1)
        self.assertEqual(target.pending("p1", 2), ["l1"])
        self.assertEqual(target.pending("p2", 2), ["l3"])


class DedupTest(unittest.TestCase):
    def test_duplicate_watch_keeps_one(self):
        target = world()
        target.watch("p1", "l1", 0)
        target.watch("p1", "l1", 10)
        self.assertEqual(target.pending("p1", 10), ["l1"])

    def test_duplicate_watch_refreshes_time(self):
        target = Watchers(per_player_max=5, ttl_ms=100, merge_ms=0)
        target.watch("p1", "l1", 0)
        target.watch("p1", "l1", 90)
        self.assertEqual(target.pending("p1", 150), ["l1"])
        self.assertEqual(target.pending("p1", 190), [])

    def test_refresh_does_not_trigger_cap_eviction(self):
        target = Watchers(per_player_max=2, ttl_ms=100000, merge_ms=0)
        target.watch("p1", "l1", 0)
        target.watch("p1", "l2", 1)
        target.watch("p1", "l1", 2)
        self.assertEqual(target.pending("p1", 3), ["l1", "l2"])


class MergeTest(unittest.TestCase):
    def test_second_change_within_merge_window_is_suppressed(self):
        target = world()
        target.watch("p1", "l1", 0)
        self.assertEqual(target.change("l1", 0), ["p1"])
        self.assertEqual(target.change("l1", 100), [])

    def test_change_exactly_at_merge_ms_notifies(self):
        target = world()
        target.watch("p1", "l1", 0)
        target.change("l1", 0)
        self.assertEqual(target.change("l1", 500), ["p1"])

    def test_merge_window_restarts_after_each_notification(self):
        target = world()
        target.watch("p1", "l1", 0)
        target.change("l1", 0)
        self.assertEqual(target.change("l1", 500), ["p1"])
        self.assertEqual(target.change("l1", 900), [])
        self.assertEqual(target.change("l1", 1000), ["p1"])

    def test_merge_is_per_listing(self):
        target = world()
        target.watch("p1", "l1", 0)
        target.watch("p1", "l2", 0)
        target.change("l1", 0)
        self.assertEqual(target.change("l2", 100), ["p1"])


class TtlTest(unittest.TestCase):
    def test_expired_watch_not_pending(self):
        target = Watchers(per_player_max=5, ttl_ms=1000, merge_ms=0)
        target.watch("p1", "l1", 0)
        self.assertEqual(target.pending("p1", 1001), [])

    def test_watch_expires_exactly_at_ttl(self):
        target = Watchers(per_player_max=5, ttl_ms=1000, merge_ms=0)
        target.watch("p1", "l1", 0)
        self.assertEqual(target.pending("p1", 999), ["l1"])
        self.assertEqual(target.pending("p1", 1000), [])

    def test_expired_watch_not_notified(self):
        target = Watchers(per_player_max=5, ttl_ms=1000, merge_ms=0)
        target.watch("p1", "l1", 0)
        target.watch("p2", "l1", 1500)
        self.assertEqual(target.change("l1", 2000), ["p2"])

    def test_expired_watch_frees_cap_slot(self):
        target = Watchers(per_player_max=1, ttl_ms=100, merge_ms=0)
        target.watch("p1", "l1", 0)
        target.watch("p1", "l2", 200)
        self.assertEqual(target.pending("p1", 200), ["l2"])


class OrderAndInvariantTest(unittest.TestCase):
    def test_pending_sorted_by_listing(self):
        target = world()
        target.watch("p1", "l3", 0)
        target.watch("p1", "l1", 1)
        target.watch("p1", "l2", 2)
        self.assertEqual(target.pending("p1", 3), ["l1", "l2", "l3"])

    def test_replaying_same_sequence_gives_same_result(self):
        def run():
            target = Watchers(per_player_max=3, ttl_ms=1000, merge_ms=100)
            target.watch("p1", "l2", 0)
            target.watch("p1", "l1", 1)
            target.watch("p1", "l1", 2)
            target.watch("p2", "l1", 3)
            first = target.change("l1", 10)
            second = target.change("l1", 50)
            return first, second, target.pending("p1", 20)

        self.assertEqual(run(), run())

    def test_scan_cost_does_not_grow_with_total_watches(self):
        target = Watchers(per_player_max=10000, ttl_ms=100000, merge_ms=0)
        for index in range(3000):
            target.watch("p-%d" % index, "l-%d" % index, 0)
        before = target.scanned_count()
        for _ in range(3000):
            target.pending("p-2999", 0)
        self.assertLessEqual(target.scanned_count() - before, 6000)
