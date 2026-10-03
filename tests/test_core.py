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


class CapTest(unittest.TestCase):
    def test_evicts_earliest_over_cap(self):
        target = Watchers(per_player_max=2, ttl_ms=100000, merge_ms=0)
        target.watch("p1", "l1", 0)
        target.watch("p1", "l2", 1)
        target.watch("p1", "l3", 2)
        self.assertEqual(target.pending("p1", 3), ["l2", "l3"])

    def test_pending_never_exceeds_cap(self):
        target = Watchers(per_player_max=3, ttl_ms=100000, merge_ms=0)
        for index in range(20):
            target.watch("p1", "l-%02d" % index, index)
            self.assertLessEqual(len(target.pending("p1", index)), 3)

    def test_cap_is_per_player(self):
        target = Watchers(per_player_max=1, ttl_ms=100000, merge_ms=0)
        target.watch("p1", "l1", 0)
        target.watch("p2", "l1", 0)
        target.watch("p1", "l2", 1)
        self.assertEqual(target.pending("p1", 2), ["l2"])
        self.assertEqual(target.pending("p2", 2), ["l1"])


class DedupTest(unittest.TestCase):
    def test_duplicate_watch_keeps_one_entry(self):
        target = Watchers(per_player_max=5, ttl_ms=100000, merge_ms=0)
        target.watch("p1", "l1", 0)
        target.watch("p1", "l1", 10)
        self.assertEqual(target.pending("p1", 10), ["l1"])

    def test_duplicate_watch_refreshes_time(self):
        target = Watchers(per_player_max=5, ttl_ms=100, merge_ms=0)
        target.watch("p1", "l1", 0)
        target.watch("p1", "l1", 90)
        self.assertEqual(target.pending("p1", 150), ["l1"])
        self.assertEqual(target.pending("p1", 190), [])

    def test_refresh_counts_as_newest_for_eviction(self):
        target = Watchers(per_player_max=2, ttl_ms=100000, merge_ms=0)
        target.watch("p1", "l1", 0)
        target.watch("p1", "l2", 1)
        target.watch("p1", "l1", 2)
        target.watch("p1", "l3", 3)
        self.assertEqual(target.pending("p1", 4), ["l1", "l3"])


class MergeTest(unittest.TestCase):
    def test_second_change_within_window_is_suppressed(self):
        target = Watchers(per_player_max=5, ttl_ms=100000, merge_ms=500)
        target.watch("p1", "l1", 0)
        self.assertEqual(target.change("l1", 0), ["p1"])
        self.assertEqual(target.change("l1", 499), [])

    def test_change_at_exactly_merge_ms_notifies(self):
        target = Watchers(per_player_max=5, ttl_ms=100000, merge_ms=500)
        target.watch("p1", "l1", 0)
        target.change("l1", 0)
        self.assertEqual(target.change("l1", 500), ["p1"])

    def test_change_after_window_notifies(self):
        target = Watchers(per_player_max=5, ttl_ms=100000, merge_ms=500)
        target.watch("p1", "l1", 0)
        target.change("l1", 0)
        self.assertEqual(target.change("l1", 600), ["p1"])

    def test_merge_window_is_per_listing(self):
        target = Watchers(per_player_max=5, ttl_ms=100000, merge_ms=500)
        target.watch("p1", "l1", 0)
        target.watch("p1", "l2", 0)
        target.change("l1", 0)
        self.assertEqual(target.change("l2", 100), ["p1"])


class TtlTest(unittest.TestCase):
    def test_pending_drops_expired(self):
        target = Watchers(per_player_max=5, ttl_ms=1000, merge_ms=0)
        target.watch("p1", "l1", 0)
        self.assertEqual(target.pending("p1", 999), ["l1"])
        self.assertEqual(target.pending("p1", 1000), [])

    def test_change_skips_expired_watchers(self):
        target = Watchers(per_player_max=5, ttl_ms=100, merge_ms=0)
        target.watch("p1", "l1", 0)
        self.assertEqual(target.change("l1", 150), [])

    def test_rewatch_after_expiry_notifies_again(self):
        target = Watchers(per_player_max=5, ttl_ms=100, merge_ms=500)
        target.watch("p1", "l1", 0)
        self.assertEqual(target.change("l1", 150), [])
        target.watch("p1", "l1", 200)
        self.assertEqual(target.change("l1", 210), ["p1"])


class OrderAndInvariantTest(unittest.TestCase):
    def test_pending_sorted_by_listing_id(self):
        target = Watchers(per_player_max=10, ttl_ms=100000, merge_ms=0)
        target.watch("p1", "l3", 0)
        target.watch("p1", "l1", 1)
        target.watch("p1", "l2", 2)
        self.assertEqual(target.pending("p1", 3), ["l1", "l2", "l3"])

    def test_replaying_same_sequence_gives_same_result(self):
        def run():
            target = Watchers(per_player_max=2, ttl_ms=1000, merge_ms=100)
            target.watch("p1", "l1", 0)
            target.watch("p1", "l2", 1)
            target.watch("p2", "l1", 2)
            target.watch("p1", "l3", 3)
            return [
                target.pending("p1", 4),
                target.change("l1", 10),
                target.change("l1", 50),
                target.change("l1", 110),
                target.pending("p2", 2000),
            ]
        self.assertEqual(run(), run())


class ScanTest(unittest.TestCase):
    def test_pending_scans_only_own_watches(self):
        target = Watchers(per_player_max=10000, ttl_ms=100000, merge_ms=0)
        for index in range(3000):
            target.watch("p-%d" % index, "l-%d" % index, 0)
        before = target.scanned_count()
        for _ in range(3000):
            target.pending("p-2999", 0)
        self.assertLessEqual(target.scanned_count() - before, 3000)

    def test_scanned_does_not_grow_with_total_watches(self):
        def scanned_for(total):
            target = Watchers(per_player_max=10000, ttl_ms=100000, merge_ms=0)
            for index in range(total):
                target.watch("p-%d" % index, "l-%d" % index, 0)
            before = target.scanned_count()
            target.pending("p-0", 0)
            target.change("l-1", 0)
            return target.scanned_count() - before
        self.assertEqual(scanned_for(100), scanned_for(10000))


if __name__ == "__main__":
    unittest.main()
