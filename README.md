# Agent Lab

A 6-stage multi-agent pipeline with enforced cost controls and human
checkpoints. Built phase-by-phase with Claude Code.

## Start here

1. Read `docs/SETUP.md`.
2. Read `specs/BUILD_PLAN.md`.
3. Open Claude Code in this folder and run `/phase`.

## What it is — and is not

A controlled pipeline orchestration tool. Not an autonomous research lab.
See `specs/ARCHITECTURE.md` for the honest scope.

## Provider

LLM provider is DeepSeek V4 (`deepseek-v4-pro` + `deepseek-v4-flash`),
called via the OpenAI SDK. See `specs/DEEPSEEK_REFERENCE.md`.
