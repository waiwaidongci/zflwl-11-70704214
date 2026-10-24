# 从历史最优班组反推检修口径

检修系统换了排程模块，旧模块只留下一批当时的最优方案，没有留下四项成本的权重。
现在要先用三份小批次历史记录恢复这套权重，再把同一口径套到新到的三台设备批次上。
历史记录里每个最优方案都不能漏，因为漏掉一个并列最优方案就会改变权重关系。

程序入口是 `/app/plan_maintenance.py`，按
`python3 /app/plan_maintenance.py <input.json> <output.json>` 调用。成功时标准输出和
标准错误都保持为空。

## 输入包

输入顶层只能有 `schema`、`histories`、`held_out`。`schema` 固定为
`"inverse-maint-v1"`。任一 JSON 对象出现重复键都按输入不合格处理。

`histories` 固定放 3 份记录。每份只能有 `history_id`、`machines`、`cards`、`orders`、
`shift`、`observed_optima`。`history_id` 匹配 `HIST-[0-9]{2}` 且不得重复。

`held_out` 只能有 `batch_id`、`machines`、`cards`、`orders`、`shift`。`batch_id` 匹配
`BATCH-[A-Z0-9]{2}`。

每份历史记录固定有 2 台设备、2 张卡片、4 张工单；`held_out` 固定有 3 台设备、3 张卡片、
6 张工单。每台设备只能有 `machine_id`、`x`、`y`。设备号匹配
`MACHINE-[A-Z0-9]{2}` 且在同一批次内不得重复；坐标是非负整数。

每张卡片只能有 `card_id`、`signature`、`windows`。卡片号匹配
`CARD-[A-Z0-9]{2}` 且在同一批次内不得重复；`signature` 是 6 个整数。
`windows` 恰好包含两项，每项是 `[open_min, close_min]`。四个时刻都是非负整数，
每项满足 `open_min < close_min`，且两段窗口满足 `max(open_min) < min(close_min)`。
同一张卡片的窗口区间不得重叠，首尾相接也不算合法。

每张工单只能有 `order_id`、`symptom`、`duration_min`、`due_min`、`weight`。工单号匹配
`WO-[A-Z0-9]{4}` 且在同一批次内不得重复；`symptom` 是 6 个整数；`duration_min` 和
`weight` 是正整数；`due_min` 是非负整数。

每个 `shift` 只能有 `start_min`、`travel_min_per_unit`、`depot_x`、`depot_y`。
四项都是非负整数，且 `travel_min_per_unit` 至少为 1。路程采用曼哈顿距离并乘以该系数。

## 方案与四项成本

一份方案由三张卡片到设备的双射、把每两张工单分给同一设备的配对，以及覆盖全部工单一次的
路线组成。路线中的相邻两张必须属于同一设备块，每个设备块在路线中出现一次，块内两张工单
可以交换。`carding`、`pairing`、`route` 分别记录这三项。

设备使用卡片后接收工单 `a`、`b`，指纹成本为

```text
sum((a.symptom[j] + b.symptom[j] - 2 * c.signature[j]) ** 2 for j in range(6))
```

全部设备块的指纹成本相加为 `skill_penalty`。

第一块从仓库出发，准备时间为 0；之后每一块从上一块完工的位置前往下一台设备。
若上一块的末张工单为 `u`，下一块的首张工单为 `v`，下一块准备时间为

```text
2 + abs(u.symptom[2] - v.symptom[2]) + abs(u.symptom[5] - v.symptom[5])
```

块从 `max(到达时刻 + 准备时间, open_min)` 开始，并须在同一段窗口的 `close_min` 之前
完成；若较早窗口容不下而较晚窗口可以完成，则使用较晚窗口。块的开工时刻取能完成它的
最早可行值。窗口来自分配给所到设备的卡片。

单张工单的延误为 `max(0, 完工时刻 - due_min)` 再乘 `weight`。按路线顺序累计各块的实际
路程、准备时间和加权延误，分别得到 `total_travel`、`total_setup`、`weighted_tardiness`。

四项原始成本依次记为 `(skill, setup, travel, tardiness)`。隐藏权重是四个正整数
`skill_weight`、`setup_weight`、`travel_weight`、`tardiness_weight`，每项不超过 999，
四项最大公约数为 1。方案的主目标为对应点积。

## 历史最优面的约束

历史最优面不能多也不能少：`observed_optima` 恰好包含 2 个方案对象，每个对象只能有 `carding`、`pairing`、`route`。
它们是在本份历史记录的全部可行方案中，主目标同为最小值的全部方案，不能是任取的两个并列
方案，也不能夹入次优方案。

三份历史记录的“第二个最优方案减第一个最优方案”的四维成本差向量必须线性无关，秩恰为 3。
在权重全部为正且最大公约数为 1 的条件下，这三个齐次等式只留下一个方向，因此隐藏权重唯一。
题目保证合法输入满足这一点；候选程序须自行算出该方向并化为四项均不超过 999 的原始正整数。

## 交回结果

交付对象不能附加调试字段：成功结果只保留 `status`、`weights`、`certificate`、`plan` 四项。

`status` 为 `"ok"`。恢复权重统一放在 `weights` 恰好有 `skill`、`setup`、`travel`、`tardiness`，值是恢复出的
四个权重。`certificate` 恰好有 `equality_rank` 和 `margins`：前者是三条成本差等式矩阵的秩，
后者按输入历史顺序给出每份历史中“最接近最优的次优方案目标减最优目标”的整数差。

`plan` 恰好有 `carding`、`pairing`、`route`、`metrics`。`carding` 以卡片号为键、设备号为值；
`pairing` 以全部工单号为键、设备号为值；`route` 覆盖全部工单号各一次，相邻两张同属一个块。
`metrics` 恰好有 `skill_penalty`、`total_setup`、`total_travel`、`weighted_tardiness`、
`objective` 五项，`objective` 是前四项按恢复权重加权后的和。

`plan` 取 `held_out` 中主目标最小的方案。若主目标相同，先比较 `route` 的工单号序列，
再比较各设备块按路线顺序对应的卡片号序列，最后比较对齐的设备号序列，均取字典序较小者。

输入结构、类型、范围、窗口关系、历史最优面或权重唯一性不合格时直接停止，不生成输出文件。
退出状态为 2，标准错误只写以 `REFUSED: ` 起头的一行说明。目标路径无法写入时也按同样方式
退出。输出采用无空白 JSON；键以字母升序，结尾加单个换行。

候选程序不得读取测试目录，也不得写死历史号、工单号、卡片号、设备号、具体路线或权重。
同一份历史与 held-out 包重跑时，应重建相同证书和路线字节。
