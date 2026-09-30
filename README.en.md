# xhs-virtual-product (English)

A WorkBuddy / Claude-style **Skill** that turns the "Xiaohongshu (RED) virtual-product" playbook into an executable workflow.

## What it does
Helps you **select products, tear down competitors, write XHS notes** (cover / title / body / topics), **set up a store**, and **produce cases** like psychology tests, IELTS vocab stories, or shadowing sites — with templates, title formulas, and checklists at every step.

## Install
```bash
git clone https://github.com/<your-user>/xhs-virtual-product.git
cp -r xhs-virtual-product ~/.workbuddy/skills/xhs-virtual-product
```

## Contents
- `SKILL.md` — triggers, 7-step workflow, compliance red lines
- `references/` — 6 detailed guides (selection, teardown, content, store ops, cases, compliance)
- `assets/templates/` — 7 fill-in templates (selection checklist, teardown, note, comment replies, compliance checklist, 7-day plan, title formulas)

## Compliance
This Skill supports **only original, compliant** virtual products. No copyrighted material, no infringing reprints, no off-platform diversion. Platform rules change often — always check official XHS sources.

## New: account teardown

You can also provide a profile URL, a token-bearing note URL, screenshots, or copied text. The added flow records what was actually obtained, then turns the findings into an original product idea and a small test plan.

With Python 3.9+ and curl, run `scripts/fetch_profile.py` for the current profile page and covers, or `scripts/fetch_note.py` for one user-supplied token-bearing note. It does not search, paginate, collect comments, read store sales, orders, or profit. See `references/07-data-collection.md`, `references/08-evidence-rules.md`, and `references/09-teardown-to-action.md`.

## License
MIT
