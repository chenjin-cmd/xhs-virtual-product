---
name: xhs-virtual-product
description: "This skill helps plan, select, produce, and market Xiaohongshu (RED) virtual/digital products — templates, knowledge bases, test tools, study materials. Use it when the user wants to build a XHS virtual-product business: do product selection, tear down competitors, write XHS notes (cover/title/body/topics), set up a store, or produce cases like psychology tests, IELTS vocab stories, or shadowing sites. Always emphasize original, compliant products (no copyrighted or infringing material)."
agent_created: true
---

# 小红书虚拟资料产品 Skill

## 何时使用

- 用户想做小红书虚拟资料 / 模板 / 知识库 / 测试类 / 学习资料产品，但缺完整路径。
- 用户要"选品""找对标账号/笔记""写商品笔记""起小红书店铺""做测试网页 / 词汇故事 PDF / 影子跟读资料库"。
- 触发词示例：小红书虚拟资料、虚拟产品、选品、对标拆解、商品笔记、小红书开店、测试类变现。

## ⚠️ 合规红线（必读，最先执行）

虚拟资料产品的底线是**只做原创、合规产品**：

- 不售卖侵权资料；不搬运带版权、机构标识、水印、授权限制的内容。
- 不使用站外导流、虚假宣传、夸大收益、诱导交易等高风险表达。
- 真正的产品用"自己的资料、自己的整理、自己的交付体系"。

执行任何制作 / 上架 / 发文动作前，先读 `references/06-compliance.md`，并用 `assets/templates/compliance-checklist.md` 逐项核查。平台规则（保证金、类目准入、营业执照等）变化快，`references/04-store-ops.md` 仅保留方法论骨架，具体数值以小红书千帆后台 / 官方文档当前规则为准。

## 主工作流（七步）

按此顺序推进，每步引用对应资料与模板：

1. **认知** — 理解"虚拟产品 = 把信息/经验/模板/工具整理成可在线交付的解决方案"。详见 `references/03-content-creation.md` 的引言部分（轻读即可）。
2. **选品** — 用 `references/01-product-selection.md` 的方法找机会，填 `assets/templates/selection-checklist.md`，并按 `assets/templates/7day-plan.md` 排期。
3. **对标** — 用 `references/02-competitor-teardown.md` 找"低粉高销量"对标，填 `assets/templates/competitor-teardown.md`（借鉴逻辑，不照搬）。
4. **制作** — 选一个案例跑通 MVP：`references/05-product-cases.md`（测试类 / 雅思词汇 / AI 编程 / 影子跟读）。
5. **上架** — 用 `references/04-store-ops.md` 完成店铺、商品信息、交付与发货配置。
6. **内容** — 用 `references/03-content-creation.md` 做封面/标题/内页/正文/话题/评论区；标题套 `assets/templates/title-formulas.md`，笔记套 `assets/templates/note-template.md`，评论区套 `assets/templates/comment-reply.md`。
7. **复盘** — 每 3 天看点击/收藏/评论/咨询/成交，回到第 2、3 步迭代产品、标题、封面与商品页。

## 输出约定

每次交付给用户时，尽量产出**结构化产物**而非泛泛建议：

- 选品阶段：一份填好的 `selection-checklist.md` + 3 个候选方向。
- 对标阶段：一份填好的 `competitor-teardown.md` + "可优化点"清单。
- 内容阶段：可直接复制的标题变体（套公式）、笔记正文、评论区话术。
- 任何上架/发文前：贴出 `compliance-checklist.md` 的核查结果。

## 资源索引

| 用途 | 文件 |
|------|------|
| 选品策略 | `references/01-product-selection.md` |
| 对标拆解 | `references/02-competitor-teardown.md` |
| 内容创作 | `references/03-content-creation.md` |
| 开店与运营 | `references/04-store-ops.md` |
| 产品案例 | `references/05-product-cases.md` |
| 合规红线 | `references/06-compliance.md` |
| 选品判断表 | `assets/templates/selection-checklist.md` |
| 对标拆解模板 | `assets/templates/competitor-teardown.md` |
| 商品笔记模板 | `assets/templates/note-template.md` |
| 评论区话术 | `assets/templates/comment-reply.md` |
| 合规检查清单 | `assets/templates/compliance-checklist.md` |
| 七天实操路径 | `assets/templates/7day-plan.md` |
| 标题爆款公式 | `assets/templates/title-formulas.md` |

## 新增：账号拆解能力

用户给出小红书账号链接、笔记链接、截图或正文时，可以用新增的账号拆解流程。旧的选品、对标、制作和内容流程保持不变；这部分只是给“对标”多了一种拿材料和整理结论的办法。

先读：

- `references/07-data-collection.md`：脚本能拿什么、拿不到什么、怎么运行。
- `references/08-evidence-rules.md`：数字、截图和不同来源对不上时怎么写。
- `references/09-teardown-to-action.md`：拆完后怎么变成自己的小产品和七天计划。

新增交付物：

- `assets/templates/evidence-ledger.md`：记来源、数字和数据缺口。
- `assets/templates/action-brief.md`：写自己的小产品、内容和下一步。

有 shell、Python 3.9+ 和 curl 时，可运行：

```bash
python3 scripts/fetch_profile.py "<账号链接或24位user_id>" -o <仓库外工作目录>
python3 scripts/fetch_note.py "<同篇带token的笔记链接>" -o <仓库外工作目录>
```

主页脚本只尝试获取当前第一页和封面；笔记脚本需要用户提供同一篇笔记的 token。搜索、翻页、评论、店铺销量、订单和利润不在脚本范围内。拿不到的数据写“未获取”，不要编造。真实账号材料、图片和 token 不进仓库。
