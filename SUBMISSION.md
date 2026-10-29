# 第三题交付说明

题目：企业知识问答 Agent。当前为评审草稿，业务尚未全部验收通过；发布结果以远程仓库及最终交卷消息为准。

| 交卷字段 | 当前值 |
|---|---|
| 题号 | 3 |
| GitHub URL | [Hoifa/RAGAgent](https://github.com/Hoifa/RAGAgent) |
| 最终 commit SHA | 见最终交卷消息；检出后可运行 `git rev-parse HEAD` 核对，本文不嵌入自身提交的SHA |
| 实现方式 | Python 3.9+ CLI、单 Agent、本地合成资料、标准库 |
| 真实模型 | 用户指定 qwen-flash；当前证据为非思考原生 Function Calling |
| 验收状态 | 有限检查30/36；AI审读另有问题，未全部通过 |
| 候选人实际总用时 | 待本人据实补充；阶段记录只有局部可核验区间 |
| 候选人独立修改与验证 | 待本人据实补充，不能将 AI 的工作写成个人独立完成 |

请先阅读 [README](README.md)、[第五阶段结果](docs/11-effect-evaluation.md) 和 [AI使用说明](docs/04-ai-usage.md)。[交付指南](docs/12-delivery.md) 给出环境、评审顺序、打包与提交步骤。

评审无需密钥即可执行：

```text
python -X utf8 -m unittest discover -s tests -v
python -m src.kb_agent.evaluate --mode mock --output-dir examples/reviewer-mock
python scripts/audit_evidence.py --report examples/stage5/verified-candidate/evaluation-results.json --require-cases A01 A02 A03 A04 A05 A06 B01 B02 B03 B04 B07 B08 B09 B11 B12 B15 B16 B17 --output-dir examples/reviewer-audit
```

前两条应成功；第三条对当前保存的真实批次返回1，因为36条中有6条有限检查失败。必须同时阅读生成的报告和 [AI审读](examples/stage5/ai-review.json)，不能把预期失败退出码当作验收通过或程序崩溃。输出目录需使用未存在的新路径。

当前主要缺口：无历史时猜主题、冲突追问把日期误当优先级依据、含糊指代追问对象不准、引文与具体断言关联，以及格式修复/预算空转。核心六类12/12仅为有限断言，不代表完整语义达标。

最终交卷消息应提供题号、仓库URL、完整40位提交SHA，并确认私有仓库评审账号可读。请勿用源码摘要或ZIP校验和代替commit SHA；不要为填写SHA再修改已提交文件而导致交卷版本变化。
