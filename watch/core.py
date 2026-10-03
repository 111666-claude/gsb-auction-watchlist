"""拍卖关注：每人上限、重复关注去重、变更通知合并与过期清理。

缺陷：每人上限不生效、同一玩家重复关注不去重、变更通知不合并、
关注不过期、每次查询扫描全部关注记录。
"""


class Watchers:
    """关注台账。"""

    def __init__(self, per_player_max, ttl_ms, merge_ms):
        self.per_player_max = per_player_max
        self.ttl_ms = ttl_ms
        self.merge_ms = merge_ms
        self.watches = []
        self.last_notify = {}
        self.scanned = 0

    def watch(self, player, listing, now_ms):
        """关注一件商品。"""
        self.scanned += len(self.watches)
        self.watches.append((player, listing, now_ms))
        return True

    def change(self, listing, now_ms):
        """商品发生变化，返回要通知的玩家。"""
        self.scanned += len(self.watches)
        out = [player for player, item, _ in self.watches if item == listing]
        self.last_notify[listing] = now_ms
        return out

    def pending(self, player, now_ms):
        """这个玩家当前有效的关注。"""
        self.scanned += len(self.watches)
        return [item for owner, item, _ in self.watches if owner == player]

    def scanned_count(self):
        return self.scanned
