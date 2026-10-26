# QuanX Rules

[![每日更新](https://github.com/akaagiao1/quanx-rules/actions/workflows/update.yml/badge.svg)](https://github.com/akaagiao1/quanx-rules/actions/workflows/update.yml)

每天自动将 [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat) 的全部分类转换为 **Quantumult X 分流规则**。包含完整版、精简版和所有 ASN 分类，自动发现新增分类。

**[查看全部分类及订阅链接](https://github.com/akaagiao1/quanx-rules/blob/quanx/index.md)** · **[同步统计](https://github.com/akaagiao1/quanx-rules/blob/quanx/reports/summary.json)** · **[更新记录](https://github.com/akaagiao1/quanx-rules/actions/workflows/update.yml)**

## 在 QuanX 中使用

在配置的 `[filter_remote]` 中添加所需分类。示例：

```ini
[filter_remote]
https://raw.githubusercontent.com/akaagiao1/quanx-rules/quanx/rules/geo/geosite/google.list, tag=Google, force-policy=proxy, update-interval=86400, enabled=true
https://raw.githubusercontent.com/akaagiao1/quanx-rules/quanx/rules/geo/geoip/telegram.list, tag=Telegram-IP, force-policy=proxy, update-interval=86400, enabled=true
https://raw.githubusercontent.com/akaagiao1/quanx-rules/quanx/rules/geo/geosite/cn.list, tag=China, force-policy=direct, update-interval=86400, enabled=true
https://raw.githubusercontent.com/akaagiao1/quanx-rules/quanx/rules/geo/geosite/category-ads-all.list, tag=Ads, force-policy=reject, update-interval=86400, enabled=true
```

把 `force-policy=proxy` 中的 `proxy` 改为自己已有的策略组名称。`direct` 和 `reject` 用于直连和拦截。所有订阅文件内部默认使用 `proxy`，项目不会根据分类名称替你决定策略。

按自己的需求选择分类，并安排好顺序；相互重叠的分类可能覆盖后面的规则。完整和精简版通常选择其一。**全部同步是指仓库覆盖所有分类，不需要把八万多个分类全部加入客户端。**

路径对照：

| 内容 | 订阅路径（接在 `/quanx/` 后） |
| --- | --- |
| 完整域名分类 | `rules/geo/geosite/<分类>.list` |
| 完整 IP 分类 | `rules/geo/geoip/<分类>.list` |
| 精简域名分类 | `rules/geo-lite/geosite/<分类>.list` |
| 精简 IP 分类 | `rules/geo-lite/geoip/<分类>.list` |
| ASN 网段 | `rules/asn/AS<编号>.list` |

## 兼容范围

输入来自上游 **sing 分支的 JSON**，每次读取同一个完整提交的压缩快照，不解析 `.dat` 或 `.srs`。分类名和目录层级保持一致，字符串和数组两种字段形式均支持。

| 输入 | 输出 |
| --- | --- |
| `domain` | `host` |
| `domain_suffix` | `host-suffix` |
| 以 `.` 开头的 `domain_suffix` | `host-wildcard,*.example.com`，保留仅匹配子域名的含义 |
| `domain_keyword` | `host-keyword` |
| IPv4 `ip_cidr` | `ip-cidr` |
| IPv6 `ip_cidr` | `ip6-cidr` |
| `domain_regex` | 无直接等价的 QuanX 分流规则；原文保存到报告，不进行近似转换 |

**全量同步分类不等于域名正则也能无损转换。** 每个源分类均有清单记录：

- `supported`：所有条目都可转换。
- `partial`：输出可转换部分，正则表达式列入 `unsupported` 报告。
- `unsupported-only`：全部是不能转换的条目，只登记报告，不提供空订阅。
- `empty`：源分类本身没有条目，只登记报告。

在产物分支 `reports/<源目录>/<页码>.json` 中可查看每个分类的源文件摘要、状态、规则数和完整遗漏内容。ASN 使用上游的实际网段，不替换成依赖其他数据库的 `ip-asn`。

未知字段、逻辑规则、反向条件、不支持的格式版本、损坏文件或下载不完整都会使本次更新失败；已发布订阅保持原样。原始规则版本目前支持 `2`。同一快照的重复运行输出一致；只有规则或来源元数据变化才创建提交。

## 自动更新

仅使用一个工作流：[`.github/workflows/update.yml`](.github/workflows/update.yml)。

- 每天**北京时间 08:30**（UTC 00:30）触发，也可在 Actions 中手动运行。
- 修改转换代码、测试或工作流后自动测试并更新；拉取请求只运行测试。
- 源码在 `main` 分支，订阅和报告在 `quanx` 分支。
- 获取完整上游快照 → 离线测试 → 全量转换与完整性检查 → 生成分类目录 → 发布普通 Git 提交，无强制推送。
- 构建任务只读权限；发布任务使用 GitHub 自带 `GITHUB_TOKEN` 的 `contents: write` 权限，无需添加个人令牌。
- 更新串行执行；如果分类数量比上次减少超过 20%，会停止发布，便于检查上游是否异常。

GitHub 定时任务可能排队或延迟；上游当天尚未完成构建时，会使用当时最新的完整快照。[GitHub 官方说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)还说明：公共仓库连续 60 天没有活动时，定时工作流会自动停用，需要重新启用。

## 创建自己的仓库

1. Fork 本仓库，或把源码上传至新公开仓库的 `main` 分支。
2. 进入 **Actions**，启用工作流，打开 **Update QuanX Rules → Run workflow** 首次运行。
3. 等待构建和发布成功；`quanx` 分支会自动创建。
4. 使用自己仓库 `quanx` 分支的 `index.md` 查找订阅地址。运行时自动使用当前仓库账号和名称，转换器无须修改。

Fork 后这份源码 README 中的链接仍指向原仓库；首次运行生成的产物分支 README 和分类目录会使用你自己的地址。若组织权限策略或分支保护阻止自动写入，需要允许工作流更新 `quanx` 分支。仓库必须公开，普通 QuanX 订阅才能直接访问 Raw 地址。

确认是上游有意大量删除分类后，可以手动运行工作流，并勾选 `allow_large_removal`。默认保持不勾选；它只解除数量减少检查，不跳过规则及文件校验。

## 本地运行

需要 Python **3.12+** 和 Git，不需要安装 Python 第三方依赖。

```sh
python3 -m unittest discover -v
python3 -m quanx_rules --repository akaagiao1/quanx-rules --output dist
```

第一次运行会下载最新上游快照。离线重现指定快照：

```sh
python3 -m quanx_rules --repository akaagiao1/quanx-rules \
  --archive .cache/<完整提交SHA>.tar.gz --sha <完整提交SHA> --output dist
```

指定某个提交进行在线下载可只传 `--sha`；`--archive` 必须配合 `--sha`。临时文件在输出目录旁边生成，全部验证成功后才替换原产物。已有目录必须含本项目的 `reports/summary.json`，以免误替换其他文件。

本地发布（先自行完成 GitHub 登录）：

```sh
gh auth setup-git
python3 -m quanx_rules.publish --output dist --remote https://github.com/akaagiao1/quanx-rules.git
```

日常使用推荐由 Actions 发布，无需在本地执行。发布失败会以非零状态结束；重复产物不会创建空提交。

## 限制与验证

当前资源上限为压缩包 1 GiB、JSON 合计 1 GiB、单个 JSON 64 MiB、分类 250,000 个；超过时明确失败，需维护者调整并验证。索引按每页 1,000 分类分页，避免 ASN 单页过大。

测试覆盖转换语义、真实压缩包遍历、目录完整性、失败保留旧文件、重复构建、分类删除、HTTP 重试及真实本地 Git 发布。另有[真实上游验证记录](docs/verification.md)。未进行 QuanX 真机导入测试。

## 来源与许可

遵循上游仓库 GPL-3.0，保留 [LICENSE](LICENSE)。外部数据源的出处、原作者及许可应一并尊重，详见 [THIRD_PARTY.md](THIRD_PARTY.md)。
