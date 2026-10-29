# 企业知识问答 Agent

小影校招 AI Agent 开发岗位考核 · 第三题。

## 当前进度

第六阶段已整理交卷说明、可复现ZIP和无密钥解压验证。112项本地测试通过；预检副本成功运行六类Mock、CLI冒烟、9组受控实验，并准确复现已有真实记录。评审先看 [SUBMISSION.md](SUBMISSION.md)、[交付指南](docs/12-delivery.md) 和 [交付验证](examples/stage6/README.md)。目标仓库为 [Hoifa/RAGAgent](https://github.com/Hoifa/RAGAgent)，最终SHA以实际提交及交卷消息为准。

第五阶段效果验证已完成：104 项本地测试、9 组受控边界实验通过；冻结版本 18 个真实案例各运行两次，有限检查通过 30/36，核心六类为 12/12。AI 审读另发现 5 次运行的问题，其中 4 次曾通过有限检查，包含核心冲突案例追问错误。因此尚未全部验收通过，不将这些数字称为完整语义正确率；全部失败及重跑保留。

2026-10-28 已结合候选人提供的旧稿补充需求，并同步接口说明、验收矩阵与阶段记录。实现基线为 Python CLI、单 Agent、本地合成知识库，运行模式统一使用 `real/mock`。

评审与后续开发入口：

- [需求与成功标准](docs/01-requirements.md)
- [接口契约](docs/06-interface-contracts.md)
- [验收矩阵](docs/07-acceptance-matrix.md)
- [阶段记录](docs/08-development-log.md)
- [实现与取舍](docs/02-solution.md)
- [实际验证与限制](docs/03-evaluation.md)
- [第五阶段效果验证](docs/11-effect-evaluation.md)
- [第五阶段运行与失败索引](examples/stage5/README.md)
- [第四阶段改进与结果](docs/10-reliability.md)
- [第四阶段真实运行索引](examples/stage4/README.md)
- [AI 使用记录](docs/04-ai-usage.md)
- [复盘草稿](docs/05-retrospective.md)
- [Qwen 联调与失败分析](docs/09-qwen-integration.md)
- [真实运行索引](examples/qwen-validation/README.md)
- [知识库说明与加载边界](data/README.md)
- [数据检查实际结果](examples/data-validation/test-results.txt)

需求文档定义业务范围和成功标准；接口契约定义字段和协议；验收矩阵定义案例及预期断言。旧稿与现有命名的对应关系见需求文档第 9 节。Mock 是预设动作播放器，只验证执行与校验，不能证明模型会根据结果调整动作。

## 环境与安装

Python 3.9+，当前验证版本 3.9.10。仅使用标准库，无需第三方依赖；`requirements.txt` 明确这一点。以下命令均在仓库根目录执行，离线模式无需密钥。

新环境先获取项目：

```text
git clone https://github.com/Hoifa/RAGAgent.git
cd RAGAgent
```

## 离线运行

```text
python -m src.kb_agent --mode mock --input tests/fixtures/inputs/A01.json --mock-script tests/fixtures/mock/A01.json --case-id A01
python -m src.kb_agent.evaluate --mode mock
```

第一条运行正常案例；第二条运行 A01—A06，包含未消解冲突、资料外问题、相似问法、上下文追问和注入的持续工具失败。每次生成新的 `examples/<case_id>/<run_id>/`，包含输入、输出、Trace；汇总追加到 `examples/evaluation-results.json`，不覆盖旧运行。

Mock 动作脚本绑定示例用途，不会理解任意新问题或自动适配文档变更。用任意问题套用脚本不能证明答案正确；真实决策使用 real 模式。

单独重现工具故障：

```text
python -m src.kb_agent --mode mock --corpus data/corpora/normal.json --input tests/fixtures/inputs/A06.json --mock-script tests/fixtures/mock/A06.json --fault-file tests/fixtures/faults/read-unavailable.json --case-id A06
```

## Qwen 真实模型运行

项目按用户选择默认使用 `qwen-flash`，地址为 `https://cn-beijing.maas.qianwenaiapi.com/compatible-mode/v1`。程序读取仓库根目录 `.env`，同名 shell 环境变量优先。只解析配置，不执行文件内容或变量插值。

首次配置时复制 `.env.example` 为 `.env`，在本地填写 `DASHSCOPE_API_KEY`。`.env.example` 保持空密钥，`.env` 已被 Git 忽略。显式 `LLM_API_KEY` 优先于 `DASHSCOPE_API_KEY`。不要提交或显示真实密钥。

模板保留 `LLM_ENABLE_THINKING=true`、`LLM_STREAM=true`、`LLM_JSON_MODE=false`，与用户提供的示例一致，未修改本地密钥配置。第五阶段验证配置为显式 `--thinking-mode off` 与默认 `LLM_ACTION_PROTOCOL=auto`：Qwen 使用原生 Function Calling，行动参数非流式传输，复核仍可流式。指代判断在同一动作循环完成，默认不再单独请求分类器。思考模式沿用 JSON 行动协议。只读取回答内容，不记录 `reasoning_content`。不同协议的实测结果不能互相代替。

模型和地址可以通过 `.env` 覆盖，程序在基础地址后追加 `/chat/completions`。缺少配置明确报错，不会切换 Mock。保留用户指定地址，接口可用性以实际联调为准。

```text
python -m src.kb_agent --mode real --corpus data/corpora/conflict.json --input tests/fixtures/inputs/A02.json --case-id A02
python -m src.kb_agent.evaluate --mode real
```

复现第五阶段验证配置，不修改本地配置：

```text
python -m src.kb_agent.evaluate --mode real --thinking-mode off --cases A01 A02 A03 A04 A05 A06 B01 B02 B03 B04 B07 B08 B09 B11 B12 B15 B16 B17 --repeat 2 --output-dir examples/my-stage5-run
```

该命令请求真实服务，生成新的输入、输出与 Trace。阶段及版本结果分批保存，见运行索引；重复运行不保证得到同一答案或成功率。已保存批次存在失败，评估和离线审计返回 1 是预期的失败报告，不代表命令崩溃。

真实模式会把问题、所提供的历史及检索/读取结果发送给配置的模型服务。项目默认资料为合成数据。默认预算：12 次模型调用、6 次工具调用，行动、适用条件核验及成功答案复核全部计数；可选适配器前置分类若启用也计数。单次超时为 60/10 秒。可通过 `--max-model-calls`、`--max-tool-calls`、`--model-timeout`、`--tool-timeout` 修改。

## 测试

在仓库根目录执行：

```text
python -m unittest discover -s tests -v
```

当前112项测试通过，覆盖协议、证据依赖、进展限制、复核隔离、数值差异、日期来源、落盘证据与交付包完整性。测试不请求外部模型，最新报告见 [完整测试结果](examples/stage6/test-results.txt)。Windows 如需强制 UTF-8，可使用 `python -X utf8 -m unittest discover -s tests -v`。

无需密钥复核已保存结果，并运行受控边界实验：

```text
python scripts/audit_evidence.py --report examples/stage5/verified-candidate/evaluation-results.json --require-cases A01 A02 A03 A04 A05 A06 B01 B02 B03 B04 B07 B08 B09 B11 B12 B15 B16 B17 --output-dir examples/my-stage5-audit
python scripts/run_boundary_checks.py --output-dir examples/my-boundary-checks
```

上述审计复用业务校验，另查工具结果重放与 Trace 关联；不能代替语义审核。输出目录使用新路径，避免覆盖原始证据。

CLI 退出码：0 表示业务执行结束且产物保存成功（业务结果仍可能为 `incomplete`，须检查 `result.status`）；2 表示输入/配置错误；3 表示产物保存失败。评估入口另用 1 表示自动状态或引用 ID 检查未通过/案例未执行。自动检查不代替语义审查。

## 后续交付

交付前优先修复无历史时猜主题、冲突追问只问日期、含糊指代追问对象错误，以及协议修复和预算空转；引用与具体断言的关联也需复核。候选人需亲自理解代码并据实补充个人贡献与实际用时，再完成 GitHub URL/最终 SHA 交付。当前不能宣称全部验收已通过。
