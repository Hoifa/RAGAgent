# 第六阶段：本地交付与复现

第六阶段整理可运行代码、依赖、文档、证据和提交说明。真实业务引擎保持第五阶段冻结版本，不通过重新挑选成功运行或修改原始记录来提高成绩。已有失败与语义问题仍是交付限制，不能称为全部达标。

## 评审顺序

1. 阅读根目录 [交卷说明](../SUBMISSION.md)，确认题号、运行方式、已知缺口及尚待补充的提交字段。
2. 阅读 [需求](01-requirements.md)、[实现取舍](02-solution.md) 和 [接口](06-interface-contracts.md)。未使用Agent框架或第三方SDK，不存在框架版本依赖；当前实测Python为3.9.10。
3. 按 [README](../README.md) 运行本地测试和Mock。Mock只验证工具、执行和校验，不作为真实ReAct证明。
4. 阅读 [真实路径](../examples/stage5/paths.md) 中正常、冲突、工具失败/恢复及正文替换路径，再查 [全部运行](../examples/stage5/final-audit/README.md)。工具参数、观察、下一动作和简短依据均可定位到原始Trace。
5. 阅读 [实际评估](11-effect-evaluation.md) 和 [AI审读](../examples/stage5/ai-review.json)，尤其是有限检查通过但语义仍有问题的样本。最后核对 [AI贡献](04-ai-usage.md) 与 [复盘](05-retrospective.md)。候选人独立理解和实际用时仍须本人补充。

## 本地打包

在项目根目录执行，无需模型密钥和网络：

```text
python scripts/build_submission.py --output dist/rag-question-3.zip
python scripts/verify_delivery.py --archive dist/rag-question-3.zip --output-dir dist/verification
```

请使用新的目标路径；脚本不覆盖已有包或验证目录。ZIP只用于本地移交与复现，不替代考试要求的GitHub仓库。

打包包含根目录交付文件、`src/`、`tests/`、`scripts/`、`data/`、`docs/`和全部`examples/`，保留历史失败。排除本地`.env`、缓存、虚拟环境、Git元数据、私钥文件和`dist/`；模板密钥必须为空，另扫描当前本地已配置密钥值是否出现在将包含的文件中。这是对已知配置值的检查，不是通用凭据识别器。

根目录`.gitattributes`关闭自动换行转换，保留引擎与历史证据原始字节；避免不同系统的`core.autocrlf`使摘要变化。没有批量改写旧Trace或制度内容。

包内`DELIVERY-MANIFEST.json`记录文件大小、SHA-256和业务引擎摘要，清单不包含自身；旁边的`.zip.sha256`记录ZIP校验和。固定文件排序、ZIP时间和权限使相同输入生成相同内容。以上摘要用于完整性核对，不是Git commit SHA，也不是验收通过证明。

## 干净目录验证

验证器先核对清单、摘要和路径，再将包解压到指定验证目录的`workspace/`。验证子进程移除模型相关环境变量，包内没有`.env`，不安装第三方依赖、不请求真实模型。执行：

- 全部本地测试。
- A01—A06六类Mock、单独CLI冒烟和9组受控边界实验。
- 重新读取36条真实记录；期望30条有限检查通过、整体退出码1。若丢文件、路径不可移植或失败数量变化则验证失败，不会仅因退出码1而放行。

原有记录使用Windows路径分隔符；离线审计现在会规范化保存路径，使其可在不同系统的检出目录定位。当前干净目录实测环境仍是Windows/Python3.9.10，不将路径修正宣称为已实测所有系统或Python版本。

验证产物位于指定`dist/`目录，包含每条命令的日志、实际退出码和包摘要。解压副本与新生成的`run-artifacts/`保留供复核；原始输入、输出和Trace不改写。完整业务引擎未修改，所以第五阶段真实证据仍对应当前源码摘要；本阶段没有产生新的真实模型效果结论。

## GitHub提交

用户已提供目标仓库 [Hoifa/RAGAgent](https://github.com/Hoifa/RAGAgent)，只读检查时远程无分支。已初始化本地`main`并仅在当前仓库配置用户提供的提交作者；不修改全局Git身份。私有仓库仍须按考试要求给指定评审账号读取权限。发布成功与否及最终SHA以实际Git结果和交卷消息为准，不虚构个人贡献。

本地Git配置和远程仓库准备好后，可按以下步骤检查并提交；命令中的目标地址由实际仓库替换：

```text
git init
git branch -M main
git remote add origin <实际GitHub仓库URL>
git add README.md SUBMISSION.md .gitignore .gitattributes .env.example requirements.txt src tests scripts data docs examples
git diff --cached --name-only
git ls-files .env
git commit -m "Submit question 3 enterprise knowledge QA agent"
git push -u origin main
git rev-parse HEAD
```

检查暂存列表后确认没有本地密钥、缓存或`dist/`；`git ls-files .env`应无输出。已有仓库时不要重复初始化或覆盖远程，先核对现状。若远程有既有提交，应正常合并，不能强推或覆盖他人内容。最终SHA应由Git实际生成，以交卷消息中的最终提交为准。

交付前仍需解决或明确记录剩余关键缺陷，并由候选人补充实际贡献、独立验证与总用时。第六阶段本地包和复现检查完成，不等于GitHub已发布或业务验收已全部通过。
