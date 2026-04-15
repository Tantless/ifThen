# AGENTS.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## 5. Project Task Workflow

**When you are making project file changes, you must follow this workflow strictly. Do not skip steps.**

Before the task:
- Confirm the repository is up to date.
- If `.trace/SUMMARY.md` does not exist, create it.
- Read the project trace in `.trace/SUMMARY.md`.
- Create `.trace/{today's date}-{daily file index}.md` as the trace file for this task, for example `.trace/03.01-1.md`.

During the task:
- At each meaningful milestone, write a progress record in `.trace/{today's date}-{daily file index}.md` in Chinese.
- Each entry should contain only one heading and describe the work completed in as much detail as possible, using concise language.
- Record only the work from this task, and only describe files that you changed yourself.
- Do not speculate about what needs to happen next or what may have been done before.
- You may refer to `.trace/SUMMARY.md`, but do not plan future work on your own.

After the task:
- Commit the current task with git.
- Write a summary of this task to `.trace/SUMMARY.md`.
- Keep the entry short. Use summary language and a list format.
- Each entry must be no longer than 10 lines. Judge the amount of work and use fewer words to summarize more.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
