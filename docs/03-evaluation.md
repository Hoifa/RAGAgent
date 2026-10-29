# 当前验证结果

日期：2026-10-28。环境：Python 3.9.10，Windows。第五阶段本地 104 项测试、9 组受控边界实验通过；冻结代码和配置两轮共 36 次真实运行，有限检查 30/36，核心六类为 12/12。AI 审读另发现 5 次运行的问题（其中 4 次自动通过），包括核心冲突案例追问错误，因此不能称全部语义验收通过。最新证据见 [第五阶段报告](11-effect-evaluation.md)、[完整运行索引](../examples/stage5/README.md) 和 [AI 审读](../examples/stage5/ai-review.json)。第三、四阶段与本页 Mock 记录均为历史，不替代当前版本证据。

2026-10-29第六阶段新增8项交付测试，当前本地共112项通过；无密钥解压副本也重现了测试、Mock与已知真实失败，见[交付验证](../examples/stage6/README.md)。业务引擎未改，没有新的真实模型效果结论；下文104项为第五阶段历史报告。

## 自动化测试

执行 `python -X utf8 -m unittest discover -s tests -v`，实际 104 项全部通过，见 [最新完整报告](../examples/stage5/test-results.txt)。覆盖 SSE、思考内容隔离、原生协议、历史角色、引用依赖、数值差异、进展限制、日期来源、复核及证据损坏等情况。早期报告仍保留。

关键风险对应证据：

| 风险 | 当前验证 |
|---|---|
| 只召回一份制度 | `test_conflict_documents_both_retrieved` 检查冲突和范围差异快照均召回双方 |
| 改写问题找不到 | `test_normal_and_rephrased_query_retrieve_same_source` 检查原问法及改写，D01 排在首位 |
| 更新正文但缓存未刷新 | `test_reload_changes_hash_without_mutating_active_snapshot` 检查新快照变更、旧快照不变 |
| 未读原文或伪造引文 | 引用拒绝、修复、失败读取不登记证据等测试 |
| 错误没有反馈模型 | 观察下一次受控模型调用确实收到 `unavailable`，不是自动隐藏错误 |
| 超限仍执行工具 | 检查工具次数不超限，同时允许最后一次读取后的合法结束 |
| 缺少模型配置偷偷用 Mock | 明确报配置错误，不回退 |
| HTTP 异常泄露信息或自动重试 | 测试只返回状态码，并确认仅一次请求 |

这些测试使用受控适配器或本地工具，不请求外部模型，不证明真实模型决策。

## 已实际运行的离线案例

执行 `python -m src.kb_agent.evaluate --mode mock`。以下每组均实际调用了本地工具并生成输出；动作和最终结果来自预设脚本。自动汇总见 [evaluation-results.json](../examples/evaluation-results.json)，其中 `react_proven=false`、`semantic_review=not_performed`。

| 案例 | 实际终态 | 输出 | Trace |
|---|---|---|---|
| A01 正常 | answered | [输出](../examples/A01/20261028T054427Z-66d398e067e0/output.json) | [Trace](../examples/A01/20261028T054427Z-66d398e067e0/trace.jsonl) |
| A02 冲突 | needs_clarification | [输出](../examples/A02/20261028T054427Z-d67db758d600/output.json) | [Trace](../examples/A02/20261028T054427Z-d67db758d600/trace.jsonl) |
| A03 资料外 | unanswerable | [输出](../examples/A03/20261028T054427Z-25e8433ce87a/output.json) | [Trace](../examples/A03/20261028T054427Z-25e8433ce87a/trace.jsonl) |
| A04 改写 | answered | [输出](../examples/A04/20261028T054427Z-80070136ce44/output.json) | [Trace](../examples/A04/20261028T054427Z-80070136ce44/trace.jsonl) |
| A05 上下文 | answered | [输出](../examples/A05/20261028T054427Z-c958f67621a1/output.json) | [Trace](../examples/A05/20261028T054427Z-c958f67621a1/trace.jsonl) |
| A06 持续故障 | incomplete | [输出](../examples/A06/20261028T054427Z-8b15fad08bfb/output.json) | [Trace](../examples/A06/20261028T054427Z-8b15fad08bfb/trace.jsonl) |

每个目录内还有实际 `input.json`。六组的状态和必需引用 ID 自动检查均通过；该检查不是完整的业务语义判定。A02 的补查、A06 的重试都是预设动作，不能作为模型根据观察自主调整的证明。

另已通过真实 CLI 入口运行一次 A01，产物位于 [CLI 冒烟记录](../examples/stage3-validation/cli-smoke/20261028T054540Z-8e2ff7491a86/output.json)。

## 开发中发现与修复的问题

首次运行评估入口因仓库根目录多取一级，报 `FileNotFoundError`，没有执行任何案例。修复根目录定位，并加入 `test_offline_evaluation_writes_actual_artifacts`，验证从评估入口到产物落盘。上述表格为修复后的真实 Mock 运行；没有用预期输出代替实际结果。

## 待验证和限制

- 当前固定版本有限检查 30/36；B02、B03、B07、B11、B16、B17 各一次失败，AI 审读还有漏项。B08 最终两次实际恢复并回答，不代表普遍恢复可靠。
- 词法检索可能漏召回或召回无关资料。目前有单查询的检索改进证据，没有大规模或语义检索对照。
- 原文子串、证据依赖、日期来源和模型复核仍不能完全验证结论蕴含关系；模型可能错用范围或遗漏限定条件。
- Qwen 鉴权、流式及思考/非思考模式已实测，其他供应商与限流尚未充分验证。
- 超时丢弃本地结果不保证远端生成已取消；不是生产级 Runtime。
- 密钥已配置在本地 `.env`，不提交；自动状态和引用 ID 检查不能证明全部语义正确。

后续扩展陌生表达、故障恢复和长文档测试；候选人核对事实、引用与个人贡献。GitHub 提交与个人独立复盘尚未完成。
