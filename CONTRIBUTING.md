# 贡献指南（中文）

感谢你考虑为 `xhs-virtual-product` 贡献力量！本 Skill 的目标是把"小红书虚拟资料"方法论变成可执行、可复用的资产。

## 你可以贡献什么

- **选品方向**：在 `references/01-product-selection.md` 补充新的细分方向或选品方法。
- **对标 / 内容技巧**：补充 `references/02-` `references/03-` 的实战经验。
- **产品案例**：在 `references/05-product-cases.md` 增加新案例（测试类 / 词汇 / 工具站 / 知识库等）。
- **模板**：在 `assets/templates/` 增加新的可填模板，并在 `SKILL.md` 资源索引中登记。
- **合规更新**：平台规则变化时，更新 `references/06-compliance.md` 与 `assets/templates/compliance-checklist.md`。

## 约定

1. **语言**：文档与模板用中文写作；示例对话保持口语化、接地气。
2. **合规红线不可弱化**：任何改动都不得暗示或鼓励侵权、搬运、站外导流、夸大宣传。新增案例必须强调"做原创版本"。
3. **结构分离**：详细知识放 `references/`，可直接复制填写的纯文本放 `assets/templates/`，核心流程与索引放 `SKILL.md`。保持 `SKILL.md` 精简（<5k 词）。
4. **时效性标注**：平台规则、第三方工具 URL、费用等易变信息，正文标注"以官方为准"，不要写死具体数值承诺。
5. **不绑定特定生态**：references / templates 是纯 Markdown，任何 Agent 或人都可直接读，不要引入只有某平台才能运行的私有格式。

## 提交方式

1. Fork 本仓库，建分支（`feat/xxx` 或 `fix/xxx`）。
2. 改动后确保 `SKILL.md` 的 frontmatter 含 `name` / `description` / `agent_created: true`。
3. 如需校验结构，运行 skill-creator 的 `package_skill.py`。
4. 提 PR，描述改动点与适用场景。

谢谢！
