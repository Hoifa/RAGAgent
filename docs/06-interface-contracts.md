# 接口契约

版本：1.1。第四阶段增加可选结束依据、原生调用元数据、问题消歧和复核事件；请求及业务输出字段、两类业务工具和终态枚举保持兼容。本文示例为说明性样例，实际证据见评估报告。

2026-10-28 随需求合并补充执行细节，工具名称、业务字段及状态枚举保持不变。业务规则见 [需求基线](01-requirements.md)，验证标准见 [验收矩阵](07-acceptance-matrix.md)。

## 1. 公共约定

- 文本与文件使用 UTF-8，结构化交换使用 JSON。
- 必填字段不得省略；空列表使用 `[]`，无追问使用 `null`。
- 文档 ID 在当前知识库中唯一；片段 ID 在所属文档内唯一。第一版同一知识库不允许一个文档 ID 对应多个版本，历史版本使用不同 ID。
- 日期采用 `YYYY-MM-DD`；非法日期、重复 ID、缺失正文在加载时拒绝，不让模型补齐。
- 每次运行使用不可变知识库快照，记录内容摘要 `corpus_revision`；检索、读取、引用验证必须使用同一快照。文档变更在下次运行生效并刷新索引。
- 运行配置与业务输入分离；密钥仅来自环境配置，不写入日志。

## 2. 业务请求

```json
{
  "question": "那需要什么材料？",
  "history": [
    {"role": "user", "content": "我想了解差旅报销。"},
    {"role": "assistant", "content": "你想了解报销的哪一方面？"}
  ]
}
```

`question` 为非空字符串；`history` 可省略，默认空数组，按时间先后排列，只允许 `user` 和 `assistant` 角色，每条 `content` 非空。非法输入在模型执行前拒绝，并返回独立的 `invalid_request` 错误，不伪装成业务终态。

空白字符串也视为空输入。第一版不新增独立 `context` 字段，地区、部门、产品版本等条件通过问题或历史携带。用户历史中的 `system/tool` 角色应拒绝，不能当作本次工具观察。追问作为本轮最终结果返回，下一次请求携带历史和补充信息继续；没有历史且指代不明时追问具体事项。

运行配置包含 `mode`（`real` 或 `mock`，默认 `real`）、知识库位置、模型配置、预算、超时、产物目录。真实模型未配置时明确报错，不静默切换 Mock。故障注入仅由测试配置开启，不由问题正文控制。

用户后续选定 `qwen-flash` 和北京接口地址作为项目默认值。根目录 `.env` 提供本地配置，shell 同名变量优先；Qwen 密钥读取 `DASHSCOPE_API_KEY`，显式 `LLM_API_KEY` 优先。`.env.example` 只保留配置示例，不填写密钥。流式、思考和 JSON 格式开关见 README。

默认预算为 12 次模型调用、6 次工具调用，单次超时仍为 60/10 秒。由 8 次增加为 12 次是为了容纳模型消歧、适用条件核验及成功答案复核；这些请求和修复全部计数，不是隐藏调用。工具参数校验失败不执行工具、不占工具额度，但模型调用已计数。

连续相同错误最多允许 3 次，达到上限返回 `incomplete/invalid_model_output`；修正了一个问题后出现不同问题不视为重复原错误，但仍受总额度约束。两次搜索无新增候选后不再接受无进展搜索；已成功读取的片段不重复执行，连续读取失败两次后要求模型换有效方式或结束。程序不据此生成业务答案。

工具额度用尽后仍可使用剩余模型额度结束；额外工具请求不执行，返回 `incomplete / budget_exhausted`。最后一次允许的模型调用生成合法最终结果且必需复核均已完成时可以完成；成功答案仍需额外核验却无额度时返回未完成。具体计数边界与需求第 5 节一致。

## 3. 文档结构

```json
{
  "document_id": "D01",
  "title": "差旅报销制度",
  "version_date": "2026-01-01",
  "passages": [
    {"passage_id": "P01", "text": "差旅报销应在行程结束后30天内提交。"}
  ]
}
```

可选元数据为 `scope`、`effective_date`、`supersedes`、`citation_dependencies`。缺省表示未知，不能推断为全员适用或当前有效。影响结论的关系必须能从原文找到依据，不能只引用后台元数据。

`citation_dependencies` 是文档作者声明的配套引文关系，例如 `{"P01":["P02"]}` 表示引用 P01 必须同时引用 P02。只允许同文档中存在的其他片段，不能自引用、重复或成环。它不包含问题、答案数值或期望状态。D06 期限条款声明其替代依据 P02 为配套引用，正文制度内容保持原样。

`passages` 必须非空，标题、文档 ID、片段 ID 和正文均为非空字符串；片段保留完整条款与起算点。D01—D06 资料组合按需求第 2.2 节组织，数据集标签、预期答案和测试断言不传给模型。

## 4. 工具公共返回

成功：`{"ok": true, "data": {...}, "error": null}`。

失败：`{"ok": false, "data": null, "error": {"code": "...", "message": "...", "retryable": false}}`。

错误码包括 `invalid_arguments`、`not_found`、`timeout`、`unavailable`、`internal_error`。`retryable` 是提示，不自动触发重试。错误消息应去除密钥、堆栈中的敏感信息等。

### search_documents

参数：

```json
{"query": "差旅 报销 提交期限", "top_k": 5}
```

`query` 必须非空；`top_k` 可省略，默认 5，范围 1—10。

成功的 `data`：

```json
{
  "corpus_revision": "<内容摘要>",
  "hits": [
    {
      "document_id": "D01",
      "title": "差旅报销制度",
      "version_date": "2026-01-01",
      "passage_id": "P01",
      "excerpt": "差旅报销应在行程结束后30天内提交。",
      "rank": 1
    }
  ]
}
```

无匹配为成功返回 `hits: []`，不是工具故障。`excerpt` 是检索候选信息，不能直接注册为最终引用证据。排序不代表权威性，返回候选不得按结论一致性去重，否则可能掩盖冲突。

### read_passage

参数：`{"document_id": "D01", "passage_id": "P01"}`，两项均必填。

成功的 `data`：

```json
{
  "corpus_revision": "<内容摘要>",
  "document_id": "D01",
  "title": "差旅报销制度",
  "version_date": "2026-01-01",
  "passage_id": "P01",
  "text": "差旅报销应在行程结束后30天内提交。"
}
```

不存在的文档或片段返回 `not_found`。数据准备应使片段包含完整条款及限定条件；需要其他条款时模型再调用工具读取，不让工具悄悄拼接无标识内容。

存在配套引文时，读取成功的 `data` 增加 `citation_dependencies`，形如 `[{"document_id":"D06","passage_id":"P02"}]`。只返回引用位置，不代读或拼接原文。模型需自行选择读取并引用；元数据不能代替原文证据。未读或未引用依赖片段时最终校验拒绝提交。

## 5. 模型行动协议

模型每轮仅返回以下一种结构，不包含内部思维过程：

工具行动：

```json
{
  "action": "tool",
  "tool_name": "search_documents",
  "arguments": {"query": "差旅报销期限", "top_k": 5},
  "reason": "需要查找问题对应的制度依据。"
}
```

结束行动：`{"action": "finish", "result": <第6节业务结果>, "reason": "简要行动依据"}`。1.1 中 `finish.reason` 可省略，此时 Trace 的 `decision_basis` 直接引用模型生成的 `result.answer`，并标注来源，不编造决策说明。工具行动的 `reason` 仍必填。

原生调用适配器可附 `provider_call_id`，仅用于关联供应商调用与工具响应。Qwen 非思考模式下，`LLM_ACTION_PROTOCOL=auto` 选用 Function Calling；思考模式或通用兼容服务继续使用 JSON 动作。`native` 和 `json` 可显式选择，原生模式当前要求非思考。

原生模式用 `finish` 函数提交业务结果，它不执行业务操作、不计为第三个业务工具。一次只接受一个调用，`tool_choice=auto`、`parallel_tool_calls=false`。若模型已返回文本却未调用函数，下一次仅强制 `finish` 的结构；模型仍决定状态、结论和引用，原文校验不放宽。原生动作使用非流式响应以完整读取参数；消歧和复核可继续使用配置的流式模式。

`reason` 只记录证据缺口或行动目的等简短说明。未知动作、未知工具、错误参数或非法最终结构须反馈校验错误，在剩余预算内由模型修正；不得偷偷转换成固定答案。

模型每次接收当前问题、历史、工具定义、已有行动和工具观察、剩余预算。是否补充检索、读取哪个片段、是否追问由模型决定。程序校验和预算机制不替代业务决策。

默认真实适配器现将指代判断放入同一模型工具循环，初轮由模型选择检索或追问，`model_configuration.reference_resolution=action_loop`。第五阶段发现前置分类既可能改写任务，也可能对明确问题过早追问，因此默认关闭，减少一次前置调用。

执行器仍支持适配器可选的 `resolve_request`：输入为结构化 `current_question/history`，不能读取资料或生成业务答案；继续时必须逐字保留问题。无读取依据的 `missing_user_context` 草稿不直接结束，而反馈 `premature_clarification` 交回正常循环。所有请求仍计预算。业务循环始终保留原请求，`runtime.resolved_question` 不替换用户任务；可选分类提示摘要记录不代表默认运行调用过该分类器。

`answered` 在结构与引文通过后，还由同一模型核验用户适用条件和事实支持。条件检查不看候选答案；事实复核不看旧拒绝输出或旧错误，减少相互暗示。第五阶段进一步将这两类复核中的历史限制为用户消息，防止历史助手错误结论被当作制度依据；业务循环仍保留原始历史。核验提出的问题回传给 Agent，仍由模型选择后续动作。其他终态保留确定性校验，避免把合理拒答误判成失败。模型复核并非语义正确性的保证。

## 6. 业务结果

```json
{
  "status": "answered",
  "reason_code": null,
  "answer": "依据D01，差旅报销应在行程结束后30天内提交。[C1]",
  "citations": [
    {
      "citation_id": "C1",
      "document_id": "D01",
      "version_date": "2026-01-01",
      "passage_id": "P01",
      "quote": "差旅报销应在行程结束后30天内提交。"
    }
  ],
  "gaps": [],
  "follow_up_question": null
}
```

约束：

- `answer` 非空；事实结论使用 `[C1]` 形式关联引用，引用 ID 唯一且不得悬空。
- 引用必须来自本次成功读取片段；`quote` 必须是其非空连续原文子串，日期和 ID 必须匹配。引用正确性还需语义评估，子串校验不是充分证明。
- `gaps` 为字符串数组，明确缺少的资料或条件；不能仅填“信息不足”。
- `answered` 要求至少一个引用、空 `gaps`、空追问和空 `reason_code`。
- `needs_clarification` 要求非空缺口和具体追问；`reason_code` 为 `document_conflict`、`missing_user_context` 或 `ambiguous_reference`。
- `document_conflict` 要求引用至少两个不同原文片段，读取后补充查证，并明确适用范围、优先级或替代关系等制度缺口。版本日期不能自动作为生效日期。当前以有限的缺口文本检查辅助约束，不能代替语义审查。
- 即使模型没有声明冲突，实际观察中同措辞而数值不同的跨文档候选也会形成 `runtime.potential_numeric_conflicts` 风险信号。`answered` 须先读取双方，并引用明确关联双方文档 ID 的适用/替代原文；不能只引用其中一方。检测范围有限且偏保守，不认定数值孰对，不将检索摘录当作正式引用。
- 未消解冲突必须列出各方不同结论及引用；已经发生但因预算或工具失败无法完成查证时使用 `incomplete`，不能冒充已经完成核查。
- `unanswerable` 要求非空缺口，原因是 `out_of_scope` 或 `insufficient_evidence`；没有证据时引用为空。
- 尚有未恢复的原文读取失败或最后一次检索失败时，不接受 `unanswerable` 或用 `needs_clarification` 将工具问题转交用户；模型需恢复或输出未完成。该检查偏保守，不判断失败读取的业务相关性。
- `incomplete` 要求非空缺口，原因是 `tool_failure`、`model_failure`、`budget_exhausted` 或 `invalid_model_output`。禁止为填满字段编造引用。

本版本没有 `partial` 状态；部分信息放入非成功结果的回答，并明确未解决部分。

冲突事项、各方规定、是否消解及其依据通过 `answer`、`citations`、`gaps` 表达，不新增 `conflicts` 字段。消解后必须引用支持替代或适用关系的原文。暂时工具错误恢复后可正常回答；若执行失败阻止必要查证，应为 `incomplete`，不能仅凭已有部分证据标为已完成。

## 7. 运行产物和 Trace

一次运行保存为 `examples/<case_id>/<run_id>/`：

- `input.json`：实际业务输入。
- `output.json`：运行元数据及业务结果。
- `trace.jsonl`：按发生顺序记录的事件。
- 测试汇总另存为 `examples/evaluation-results.json`，关联案例和运行目录。

输出封装由程序生成，包含 `run_id`、`mode`、`corpus_revision`、模型标识（Mock 时明确标注）、生效预算、模型和工具实际调用次数、`result`。模型不得自行填写运行元数据。

1.1 增加 `runtime_version`、导入时计算的源码 `engine_revision` 和 `resolved_question`；运行配置记录动作协议及各提示摘要。模型调用次数包含消歧、动作和两类成功答案复核。

运行层负责管理产物位置，不新增模型生成的 `trace_path` 字段。只有文件确实写入成功才能报告已保存。写入失败属于运行层错误：通过标准错误输出明确说明并使 CLI 非零退出，不伪造文件路径或强行归入某个模型业务原因码；已经生成的业务结果与证据保存失败应分别报告。

Trace 每条包含 `event_id`、`timestamp`、`step`、`type`、`data`。事件类型：`run_started`、`model_action`、`tool_result`、`validation_error`、`run_finished`。工具行动和结果通过 `call_id` 关联。

增加运行诊断事件 `model_error`，只记录适配器已脱敏的连接、HTTP 状态或超时错误。返回供应商的完整错误体及思考内容不进入 Trace。输出运行元数据可包含 `model_configuration`：端点、流式/思考/JSON 开关和提示内容摘要。

1.1 新增 `request_resolution`、`review_started`、`applicability_review`、`evidence_review` 事件。每次模型调用都有计数；同一个候选答案的复核通过 `candidate_step` 关联。`no_progress` 为未执行重复工具的校验提示，不假造工具返回。

`model_action` 保存规范化行动、参数及简要依据；`tool_result` 保存成功标记、返回摘要和完整结构化返回，支持审查究竟给模型看了什么。后续 `model_action` 即该观察后的动作，无须提前伪造“下一步”。Trace 不保存密钥或模型内部思维过程。

故障或结果注入配置由运行层在 `run_started` 中记录；每次注入在相应 `tool_result` 中标识。真实模型参与但工具结果经过注入的运行仍需明确这一边界，不能宣称为自然检索质量证据。保留失败运行和重跑记录，不覆盖同一案例的旧产物。

数据加载或输入校验失败的启动错误单独返回结构化错误，CLI 进程退出非零；有效业务终态（包括不能回答）与程序崩溃区别对待，后续实现文档需给出明确退出码映射。

当前 CLI 映射：0 为业务结束且产物保存成功（仍需查看 `result.status`）；2 为输入或配置错误；3 为产物写入失败。评估入口另以 1 表示自动断言失败或所选案例未运行。无效模型输出持续到预算耗尽时为 `incomplete / budget_exhausted`，Trace 保留各次校验失败，不能解释成普通业务无资料。

评估入口支持 `--repeat N`，保持配置不变重复全部所选案例；每完成一条即原子追加汇总，程序中断不丢失此前汇总。断言留在测试侧，包括具体事实、原文片段、工具错误观察与停止状态；不传给模型。真实结果的 `react_proven=null` 表示自动评估不代替人工 Trace 审查，Mock 仍为 false。

超时实施边界：有界等待丢弃超时结果，HTTP 同时设置连接/读取超时。本地后台只读工作可能短暂继续，但不能追加证据或启动下一行动；不保证远端生成和计费被取消。故障注入和预算均在运行元数据中可检查。
