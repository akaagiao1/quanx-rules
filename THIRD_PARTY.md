# 来源与第三方声明

本项目转换的数据直接来自 [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat) 的 `sing` 分支。输出保留分类路径；`reports/summary.json` 记录完整来源提交，每分类清单记录源 JSON 的 SHA-256。

本仓库保留上游 `master/LICENSE` 的 GNU General Public License version 3 原文。本项目的转换程序使用 GPL-3.0-only 发布。生成的数据涉及上游汇集的多个外部项目；保留上游仓库许可证不表示所有外部原始数据都采用相同许可证。

上游 [README](https://github.com/MetaCubeX/meta-rules-dat/blob/master/README.md) 列出的来源包括：

- [Loyalsoldier/v2ray-rules-dat](https://github.com/Loyalsoldier/v2ray-rules-dat)
- [Loyalsoldier/geoip](https://github.com/Loyalsoldier/geoip)
- [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community)
- [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)
- 其他域名及 IP 列表：以对应来源提交的上游说明和构建流程为准。

ASN JSON 由上游转换流程中的 [MetaCubeX/meta-rules-converter](https://github.com/MetaCubeX/meta-rules-converter) 从 ASN 数据生成。具体数据许可及归属请同时参照上游当时的来源与声明。本项目没有随仓库分发上游的 MMDB、DAT、SRS 二进制数据库。

Quantumult X 规则语法参考其作者的[官方示例配置](https://github.com/crossutility/Quantumult-X/blob/master/sample.conf)。本项目不是 Quantumult X 官方项目，与客户端作者不存在隶属关系。
