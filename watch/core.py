"""拍卖关注：每人上限、重复关注去重、变更通知合并与过期清理。

实现口径（见 README）：
- 每人最多保留 per_player_max 条关注，超出移除最早的一条；
- 同一玩家重复关注同一件商品只刷新时间，不新增记录；
- 同一商品距上次通知不足 merge_ms 不再通知，等于 merge_ms 可以通知；
- 关注存在时间达到 ttl_ms 后失效，pending 不返回也不再通知；
- pending 按商品 id 升序；watch/change/pending 只访问涉及的玩家或
  商品索引，不扫描全部关注记录。
"""


class Watchers:
    """关注台账。"""

    def __init__(self, per_player_max, ttl_ms, merge_ms):
        self.per_player_max = per_player_max
        self.ttl_ms = ttl_ms
        self.merge_ms = merge_ms
        # player -> {listing: since_ms}，按关注时间有序（刷新时间会移到末尾）。
        self.by_player = {}
        # listing -> set(player)，变更时只触及该商品的关注者。
        self.by_listing = {}
        self.last_notify = {}
        self.scanned = 0

    def _expired(self, since_ms, now_ms):
        return now_ms - since_ms >= self.ttl_ms

    def _drop(self, player, listing):
        items = self.by_player.get(player)
        if items is not None:
            items.pop(listing, None)
            if not items:
                del self.by_player[player]
        watchers = self.by_listing.get(listing)
        if watchers is not None:
            watchers.discard(player)
            if not watchers:
                del self.by_listing[listing]

    def _purge_player(self, player, now_ms):
        items = self.by_player.get(player)
        if not items:
            return
        for listing, since_ms in list(items.items()):
            self.scanned += 1
            if self._expired(since_ms, now_ms):
                self._drop(player, listing)

    def watch(self, player, listing, now_ms):
        """关注一件商品；重复关注只刷新时间，超出上限移除最早的一条。"""
        self._purge_player(player, now_ms)
        items = self.by_player.setdefault(player, {})
        if listing in items:
            # 去重：刷新时间，并保持按关注时间有序。
            del items[listing]
            items[listing] = now_ms
            return True
        items[listing] = now_ms
        self.by_listing.setdefault(listing, set()).add(player)
        while len(items) > self.per_player_max:
            self._drop(player, next(iter(items)))
        return True

    def change(self, listing, now_ms):
        """商品发生变化，返回要通知的玩家（按玩家 id 升序）。"""
        watchers = self.by_listing.get(listing)
        if not watchers:
            return []
        last = self.last_notify.get(listing)
        if last is not None and now_ms - last < self.merge_ms:
            return []
        out = []
        for player in sorted(watchers):
            self.scanned += 1
            items = self.by_player.get(player)
            since_ms = items.get(listing) if items else None
            if since_ms is None:
                watchers.discard(player)
                continue
            if self._expired(since_ms, now_ms):
                self._drop(player, listing)
                continue
            out.append(player)
        if not watchers:
            self.by_listing.pop(listing, None)
        if out:
            self.last_notify[listing] = now_ms
        return out

    def pending(self, player, now_ms):
        """这个玩家当前有效的关注，按商品 id 升序。"""
        items = self.by_player.get(player)
        if not items:
            return []
        out = []
        for listing, since_ms in list(items.items()):
            self.scanned += 1
            if self._expired(since_ms, now_ms):
                self._drop(player, listing)
            else:
                out.append(listing)
        return sorted(out)

    def scanned_count(self):
        return self.scanned
