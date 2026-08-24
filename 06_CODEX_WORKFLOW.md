# CODEX WORKFLOW — SIH26-26153

## Rule
Use Codex as a bounded engineering agent, not as the project architect.

## Before Every Task
Provide:
1. exact file/module
2. exact acceptance criteria
3. existing interface
4. tests required
5. constraints

## Prompt Template
```text
You are working on SIH26-26153.

Role:
[role]

Task:
[ONE task]

Read first:
[files]

Must preserve:
- canonical feature schema
- existing public interfaces
- offline execution

Acceptance criteria:
- ...
- ...

Tests:
- ...

Do not:
- redesign architecture
- add unrelated dependencies
- modify other modules unnecessarily
- fabricate results
```

## Good Codex Tasks
- one parser
- one feature transformer
- one model
- one metric
- one test suite
- one UI component
- one bug fix
- one refactor

## Bad Codex Tasks
- "Build the whole project"
- "Make it state of the art"
- "Add every model"
- "Improve AI however you want"

## PR Rule
Every Codex PR must be runnable, tested, small enough to review, and tied to a PS requirement.
