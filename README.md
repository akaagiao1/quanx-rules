# QuanX 自动更新规则

[全部分类](index.md) · [同步报告](reports/summary.json) · [使用说明](https://github.com/akaagiao1/quanx-rules)

分类：84,596；订阅文件：84,587；规则：2,408,674；无法转换的域名正则：405。

每天北京时间 08:30 自动更新，GitHub 调度可能延迟。所有文件默认策略为 `proxy`。

```ini
[filter_remote]
https://raw.githubusercontent.com/akaagiao1/quanx-rules/quanx/rules/geo/geosite/google.list, tag=Google, force-policy=proxy, enabled=true
```

使用时将 `proxy` 换成自己已有的策略组名称。partial 分类仅含可转换部分，详见 reports 对应分页中的 unsupported 字段。

来源：[MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat)。来源声明与许可证见 THIRD_PARTY.md 和 LICENSE。
