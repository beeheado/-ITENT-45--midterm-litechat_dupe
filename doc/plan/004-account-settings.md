# Plan 004: Account and settings page

Timestamp: 2026-09-30T00:35:00-07:00 (approximate)
Based on: `doc/study/003-account-settings.md`
Status: approved; executing on `feat/account-settings`

No new dependencies.

## M0: Safety
- [ ] `chore:` `DJANGO_DB_PATH` so smoke tests use a scratch database, and record the rule in `CLAUDE.md`

## M1: Models
- [ ] `feat:` `UserProfile` and `MemoryItem` models, migration, backfill for existing users
- [ ] `feat:` create the profile in the user post-save signal; `profile_for(user)` accessor
- [ ] `feat:` admin registration
- [ ] `test:` auto-creation, backfill, per-user isolation

## M2: Account page shell
- [ ] `feat:` `/account/` route, view, template with profile and billing cards, Back to App
- [ ] `feat:` header "Account" link, flash messages rendering in `base.html`
- [ ] `feat:` CSS for switch, segmented control, badges
- [ ] `test:` login required, exact spec strings, date format, display-name fallback, `$2.00` formatting

## M3: System prompt
- [ ] `chore:` capture real system-prompt behaviour for all three providers (fixtures)
- [ ] `feat:` `system` on `ChatRequest`, adapter mapping, `build_system_prompt`
- [ ] `feat:` reserve estimate counts the system text
- [ ] `feat:` save-prompt form and view (4000 char cap)
- [ ] `test:` adapter bodies, prompt reaches the adapter through `send`, edits apply to existing chats

## M4: Memories
- [ ] `feat:` add and delete memory items (500 chars, 50 cap), list and empty state
- [ ] `feat:` auto-memory toggle (stored only)
- [ ] `feat:` memories injected into the system text
- [ ] `test:` CRUD, ownership, cap, escaping, injection

## M5: Default app
- [ ] `feat:` segmented control persists the choice; `LoginView` subclass lands per `APP_HOME`
- [ ] `test:` persistence, active state, login redirect

## M6: Verify and sync
- [ ] `chore:` live check on a scratch DB with all three providers (system prompt + memory obeyed)
- [ ] `chore:` screenshots desktop and phone, both themes
- [ ] `docs:` wiki sync, retrospective, transcripts, leak check, push
