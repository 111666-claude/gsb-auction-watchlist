# auction-watchlist

拍卖关注：每人上限、重复关注去重、变更通知合并与过期清理，只用 Python 标准库。

```
python3 -m watch.cli --sample cap
python3 -m watch.cli --sample dedup
python3 -m watch.cli --sample merge
python3 -m watch.cli --sample ttl
python3 -m watch.cli --sample scan
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **每人上限**：同一个玩家最多保留 `per_player_max` 条关注，超出时移除该玩家
  最早的一条。
- **去重**：同一个玩家关注同一件商品只保留一条，重复关注只刷新时间。
- **变更通知**：同一件商品距上次通知不足 `merge_ms` 时不再重复通知，
  返回空列表；正好等于 `merge_ms` 可以通知。
- **过期**：关注存在时间达到 `ttl_ms` 后失效，`pending` 不再返回，
  也不会再收到通知。
- **顺序**：`pending` 按商品 id 升序返回。
- **不变量**：`pending` 条数不超过 `per_player_max`；同一串关注与变更序列
  重复执行结果相同。
- **查询代价**：`pending` 与 `change` 不许扫描全部关注记录，`scanned_count`
  不随关注总数线性增长。
- **规模**：10 万条关注、每秒 10 万次查询，单次摊还 O(变更涉及的人数)。

## 输出契约（不改格式）

```
pending=..
second=..
scanned=..
```

## 目录

```
watch/core.py   上限、去重、合并与过期
watch/cli.py    命令行入口
tests/          unittest 用例
```
