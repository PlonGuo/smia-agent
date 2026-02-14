# Initializer Phase Design

## Context

SmIA is a dual-interface AI intelligence platform (React web app + Telegram bot) that aggregates and analyzes social media data from Reddit, YouTube, and Amazon. The full product design lives in `PRD.md`.

This document captures decisions for the initializer phase — setting up the project skeleton and tooling.

## Decisions

### Approach
- Sequential execution of CLAUDE.md steps 1-7
- Article learnings inform project structure before scaffolding

### YARS Integration
- Clone from `https://github.com/PlonGuo/yars.git` (not pip install)
- Reference locally in the backend

### Project Structure
- Follow PRD Section 4.3 exactly
- Backend: `api/` with uv, FastAPI, PydanticAI
- Frontend: `frontend/` with Vite, React 19, Chakra UI v3
- Root: vercel.json, .env.example

### Database
- Supabase MCP for table creation
- Tables: `user_bindings`, `analysis_reports` per PRD Section 6.1
- RLS policies enabled from day one

### Environment
- API keys in `local.env` (gitignored)
- `.env.example` with placeholder values for onboarding

## Steps

1. Read Anthropic harness article + find quickstart repo
2. Create `features.md` (PRD breakdown by phase)
3. Create `claude-progress.txt`
4. Scaffold backend (uv project, deps, directory structure)
5. Scaffold frontend (Vite + React + Chakra UI)
6. Configure Vercel (vercel.json)
7. Set up Supabase tables + RLS
8. Commit + push
