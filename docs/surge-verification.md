# Surge 扩展验证

日期：2026-10-31（Asia/Shanghai）。

## 当前全量快照

来源：MetaCubeX/meta-rules-dat sing 提交 `3a27e598be95d745b8652860b1337157a8822943`。

单次下载之后，以完全相同的快照分别生成 QuanX 和 Surge。两者各处理 84,752 个分类，生成 84,743 个非空订阅文件、2,408,638 条去重后的规则。分类包含 82,439 个 ASN、2,017 个完整域名、260 个完整 IP、24 个精简域名和 12 个精简 IP。

两种格式均完整支持 84,686 个分类，部分支持 57 个分类；9 个仅含正则的分类只进入报告。405 条无法等价转换的域名正则原文保留在各自产物分支的清单中。

构建过程重新校验了全部输出文件的哈希、规则类型、字段数及清单统计；Surge 额外检查单个规则集不超过客户端 1,000,000 条上限。

## QuanX 兼容性

使用初始提交 `d6a46777aa9438e4f718fdbbc0e42768a3dc62ea` 再次构建，比较之前保存的 SHA-256：所有 **84,494 个 QuanX 规则文件逐字节一致**。原有 `quanx` 分支和 Raw 订阅路径不变。CLI 不传 `--format` 时仍只生成 QuanX；旧报告未记录 format 时仍按 QuanX 处理。

## Surge 原生离线检查

使用 Surge 自带 `surge-cli --check` 检查临时配置，不启动 Surge，也不修改用户实际配置。

- 六种原生类型的 fixture：DOMAIN、DOMAIN-SUFFIX、DOMAIN-KEYWORD、DOMAIN-WILDCARD、IP-CIDR、IP-CIDR6 均通过。
- 将真实生成的 Google 域名、Telegram IP、精简 OpenAI 和 ASN AS13335 内容放入临时内联 Ruleset，均返回 `OK`。
- 负向对照中，未知规则类型 NOT-A-RULE 被原生检查器明确拒绝并返回非零状态，确认检查实际解析规则集内容。

未进行运行时连接测试；检查不依赖用户的在线代理配置。

## 自动测试与发布流程

Python 3.12：**33 项测试通过**，包含所有原有测试，以及 Surge 类型/策略省略、正则报告、专属目录链接、格式混写拒绝、Surge 分支自动选择、过大规则集拒绝、旧报告兼容与双格式 CLI 集成测试。

工作流保持一个，每天 UTC 00:30（北京时间 08:30）运行。双格式全部构建成功后才开始发布；发布到各自的 quanx 与 surge 分支，格式不匹配时拒绝推送。每次使用普通 Git 提交，不强制推送。工作流通过 actionlint 检查。

两种格式各校验 84,834 个分类目录及订阅链接，均对应实际文件。最大规则集为 geo/geoip/us，261,288 条。

## GitHub 部署验收

[首次双格式更新 #41181495637](https://github.com/akaagiao1/quanx-rules/actions/runs/41181495637) 的 build 和 publish 均成功。产物提交：Surge `149d4731038a9d5616bc9f3e679e04f9b10226e6`，QuanX `3969fc7e9bdd17f254f87a84bf626db0f54cde95`。

两个分支的公开 Raw 报告均确认来源快照为 `3a27e598be95d745b8652860b1337157a8822943`，分类数和规则数与本地验证一致。Surge 的 Google、Telegram IP、精简 OpenAI、AS13335、分类目录，以及原有 QuanX Google 地址均实际访问成功，首条规则的类型和字段数正确。

独立只读代码审阅未发现 Critical、Important 或 Minor 问题；另行复核了全量清单一致性、旧 QuanX 内容兼容性和原生离线检查。实际在线路由与 QuanX 真机导入不在本次验证范围。

## 参考

- [Surge RULE-SET 格式和单集条数限制](https://manual.nssurge.com/rules/ruleset.html)
- [Surge 域名匹配语义](https://manual.nssurge.com/rules/domain.html)
- [Surge IPv4 / IPv6 类型](https://manual.nssurge.com/rules/ip.html)
