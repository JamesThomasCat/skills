---
name: software-development-instruction-rules
description: 制定或评审软件开发全生命周期的约束、阶段门禁、交付证据与跨阶段追踪，覆盖需求、设计、治理、实现、验证、发布、运维和退役。用户询问 development rules、lifecycle gates、requirements traceability、design review、release readiness，或“能否开工/合并/上线”“交付是否完整”“如何做全流程审计”时使用；普通编码任务和单纯概念问答无需启用。
---

# 软件开发阶段门禁规则

将软件生命周期约束作为可执行的阶段门禁。除非用户明确修改规则，否则“必须”和“不得”均为阻断性要求。

## 语言

- 按用户当前请求的语言回答：中文请求用中文，英文请求用英文。用户指定语言或要求双语时，遵照其要求。请求中英文混用且未指定语言时，以实质需求使用的语言为准。
- 需求编号、文件名、命令、代码、接口字段和原文引述保持不变。说明文字、阶段名称、证据说明及待办事项使用回答语言。翻译不得降低门禁要求的强度。
- 中文报告使用“通过（PASS）”“有条件通过（CONDITIONAL）”“阻断（BLOCKED）”“未评估（NOT_ASSESSED）”；英文报告使用相应英文代码。中文报告保留英文状态代码，便于检索和对照。
- 需要双语交付时，对应的中英文内容应并列呈现，两种语言中的门禁结论、证据和待办事项必须一致。

## 按需加载

先确定用户是在制定规则、评审就绪情况，还是处理某个交付物；再按阶段和风险选择参考文件。只读取当前任务相关的文件；跨阶段问题读取涉及的几个阶段，全流程审查再依次读取全部阶段。普通概念解释无需套用门禁报告；未检查项目证据时，不要仅凭本索引判断门禁通过或阻断。

### 治理与方法

- 制定通用规范、执行门禁判定、处理跨阶段追踪或输出审查结论：读取 [全流程控制与判定](references/governance/controls.md)。
- 选择裁剪强度，或处理存量系统、紧急修复、高风险迁移、受监管交付、公共库和 AI 系统：读取 [风险配置与适用性](references/governance/risk-profiles.md)。
- 形成可重复审计、控制矩阵、例外记录或机器可读结果：读取 [控制编号与证据记录](references/governance/evidence-and-control-ids.md)。
- 制定工作分解、工期估算、依赖或进度预测：读取 [计划与估算方法](references/governance/planning-estimation.md)。
- 涉及采购、外包、SaaS、商业组件、开源准入或供应商退出：读取 [采购与供应商控制](references/governance/acquisition-and-suppliers.md)。

### 生命周期阶段

- 立项、可行性、目标与交付计划：读取 [阶段一：立项与可行性分析](references/lifecycle/01-initiation.md)。
- 需求获取、分析、确认、变更与追踪：读取 [阶段二：需求分析](references/lifecycle/02-requirements.md)。
- 业务建模、架构、接口、数据与详细设计：读取 [阶段三：系统与详细设计](references/lifecycle/03-design.md)。
- 编码、代码审查、依赖与迁移实现：读取 [阶段四：编码实现](references/lifecycle/04-implementation.md)。
- 测试、缺陷、回归与业务验收：读取 [阶段五：验证与确认](references/lifecycle/05-verification.md)。
- 部署、数据切换、发布与恢复：读取 [阶段六：部署与发布](references/lifecycle/06-release.md)。
- 监控、故障、维护与持续改进：读取 [阶段七：运行与维护](references/lifecycle/07-operations.md)。
- 下线、数据处置与资源清理：读取 [阶段八：系统退役](references/lifecycle/08-retirement.md)。

### 工程保证专题

- 选择、检查或维护 UML、业务流程、数据和架构模型：读取 [建模方法与一致性检查](references/engineering/modeling-methods.md)。
- 涉及身份权限、威胁建模、源码托管、CI/CD、依赖、SBOM、构建来源证明、签名或制品分发：读取 [安全设计与软件供应链](references/engineering/security-supply-chain.md)。
- 涉及个人信息、敏感数据、测试数据、数据共享、保留删除或隐私影响评估：读取 [隐私与数据治理](references/engineering/privacy-data-governance.md)。
- 涉及安全漏洞、披露、补丁、公告、在役版本或支持终止：读取 [漏洞响应与产品支持](references/engineering/vulnerability-response.md)。
- 涉及 AI 辅助编码、机器学习模型、生成式 AI、训练数据或模型更新：读取 [AI 辅助开发与 AI 系统](references/engineering/ai-assisted-and-ai-systems.md)。

参考文件中的“必做事项、所需证据、退出门禁”共同构成该阶段的约束。方括号中的稳定控制编号用于引用和追踪，不代表所有控制都自动适用。规则制定可以从中选取适用条款；就绪评审需要检查证据并读取 [全流程控制与判定](references/governance/controls.md)。若任务跨越相邻阶段，同时读取相关文件，并说明阶段间的输入、输出与未决风险。不得因为引用了本技能，就自动创建文档、调用外部服务或要求额外审批。
