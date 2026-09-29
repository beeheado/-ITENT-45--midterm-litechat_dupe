# Plan 004: Account and settings page

Timestamp: 2026-09-30T00:35:00-07:00 (approximate)
Based on: `doc/study/003-account-settings.md`
Status: executed on `feat/account-settings`

No new dependencies.

## M0: Safety
- [x] `chore:` `DJANGO_DB_PATH` so smoke tests use a scratch database, and record the rule in `CLAUDE.md`

## M1: Models
- [x] `feat:` `UserProfile` and `MemoryItem` models, migration, backfill for existing users
- [x] `feat:` create the profile in the user post-save signal; `profile_for(user)` accessor
- [x] `feat:` admin registration
- [x] `test:` auto-creation, backfill, per-user isolation

## M2: Account page shell
- [x] `feat:` `/account/` route, view, template with profile and billing cards, Back to App
- [x] `feat:` header "Account" link, flash messages rendering in `base.html`
- [x] `feat:` CSS for switch, segmented control, badges
- [x] `test:` login required, exact spec strings, date format, display-name fallback, `$2.00` formatting

## M3: System prompt
- [x] `chore:` capture real system-prompt behaviour for all three providers (fixtures)
- [x] `feat:` `system` on `ChatRequest`, adapter mapping, `build_system_prompt`
- [x] `feat:` reserve estimate counts the system text
- [x] `feat:` save-prompt form and view (4000 char cap)
- [x] `test:` adapter bodies, prompt reaches the adapter through `send`, edits apply to existing chats

## M4: Memories
- [x] `feat:` add and delete memory items (500 chars, 50 cap), list and empty state
- [x] `feat:` auto-memory toggle (stored only)
- [x] `feat:` memories injected into the system text
- [x] `test:` CRUD, ownership, cap, escaping, injection

## M5: Default app
- [x] `feat:` segmented control persists the choice; `LoginView` subclass lands per `APP_HOME`
- [x] `test:` persistence, active state, login redirect

## M6: Verify and sync
- [x] `chore:` live check on a scratch DB with all three providers (system prompt + memory obeyed)
- [x] `chore:` screenshots desktop and phone, both themes
- [x] `docs:` wiki sync, retrospective, transcripts, leak check, push

## Notes
- Live check used a scratch database (`DJANGO_DB_PATH`); the developer's `db.sqlite3` was not touched.
- Real proxy captures for system prompts: `fixtures/proxy/*/stream_system_prompt.txt`.
- Not verified by an agent in an interactive browser: switch auto-submit and segmented clicks (plain POST forms, covered by tests); the human should click through once.
