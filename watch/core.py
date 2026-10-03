"""拍卖关注：每人上限、重复关注去重、变更通知合并与过期清理。

实现口径（与 README 一致）：
- 每个玩家一本按关注时间排序的台账：重复关注只刷新时间并视为最新一条，
  超出 per_player_max 时移除最早一条（过期记录时间最早，总是先被移除）。
- 每件商品一份关注者索引：change 只遍历这件商品的关注者，
  距上次通知不足 merge_ms 直接返回空列表，正好等于 merge_ms 可以通知。
- pending / change 只遍历目标玩家或目标商品的记录，不扫描全部关注，
  scanned_count 不随关注总数线性增长；过期记录在遍历时顺手清理。
"""


class Watchers:
    """关注台账。"""

    def __init__(self, per_player_max, ttl_ms, merge_ms):
        self.per_player_max = per_player_max
        self.ttl_ms = ttl_ms
        self.merge_ms = merge_ms
        # player -> {listing: 关注时间}，按最近一次关注排序
        self.by_player = {}
        # listing -> {player: 关注时间}，按首次关注顺序
        self.by_listing = {}
        # listing -> 上次通知时间
        self.last_notify = {}
        self.scanned = 0

    def _expired(self, ts, now_ms):
        """关注存在时间达到 ttl_ms 即失效。"""
        return now_ms - ts >= self.ttl_ms

    def watch(self, player, listing, now_ms):
        """关注一件商品：重复关注只刷新时间，超出上限移除最早一条。"""
        watches = self.by_player.setdefault(player, {})
        if listing in watches:
            # 去重：只刷新时间，并视为该玩家最新的一条
            del watches[listing]
        watches[listing] = now_ms
        self.by_listing.setdefault(listing, {})[player] = now_ms
        if len(watches) > self.per_player_max:
            oldest = next(iter(watches))
            del watches[oldest]
            self.scanned += 1
            backers = self.by_listing.get(oldest)
            if backers is not None:
                backers.pop(player, None)
                if not backers:
                    del self.by_listing[oldest]
        return True

    def change(self, listing, now_ms):
        """商品发生变化，返回要通知的玩家；不足 merge_ms 不重复通知。"""
        last = self.last_notify.get(listing)
        if last is not None and now_ms - last < self.merge_ms:
            return []
        watchers = self.by_listing.get(listing)
        if not watchers:
            return []
        self.scanned += len(watchers)
        out = []
        stale = []
        for player, ts in watchers.items():
            if self._expired(ts, now_ms):
                stale.append(player)
            else:
                out.append(player)
        for player in stale:
            del watchers[player]
            mine = self.by_player.get(player)
            if mine is not None:
                mine.pop(listing, None)
                if not mine:
                    del self.by_player[player]
        if not watchers:
            del self.by_listing[listing]
        if out:
            self.last_notify[listing] = now_ms
        return out

    def pending(self, player, now_ms):
        """这个玩家当前有效的关注，按商品 id 升序返回。"""
        watches = self.by_player.get(player)
        if not watches:
            return []
        self.scanned += len(watches)
        for item, ts in list(watches.items()):
            if self._expired(ts, now_ms):
                del watches[item]
                backers = self.by_listing.get(item)
                if backers is not None:
                    backers.pop(player, None)
                    if not backers:
                        del self.by_listing[item]
        if not watches:
            del self.by_player[player]
            return []
        return sorted(watches)

    def scanned_count(self):
        return self.scanned
