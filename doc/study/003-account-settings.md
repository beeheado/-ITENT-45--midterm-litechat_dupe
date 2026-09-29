# Study 003: Account and settings page

Timestamp: 2026-09-30T00:30:00-07:00 (approximate)
Status: approved by the user (scope questions answered)

## 1. Goal
One page where a user sees their account, sets a global system prompt, manages memory items, picks a default landing app, and sees their credit. The prompt and memories must actually change how chats behave, not just be stored.

## 2. Decisions asked of the user
| Question | Answer |
|---|---|
| SimGen and Ask do not exist in Darkchat. What should the Default App selector do? | Save all three; login lands on Chat for any choice until those apps exist. |
| "Generate AI Memories" implies an LLM reading past chats. Build it now? | No. Store the setting only; generation is a separate study (cost, privacy, dedupe, billing). |

## 3. Options and tradeoffs
**Where to store the new per-user settings**
| Option | Pros | Cons |
|---|---|---|
| Custom user model / fields on `User` | One table | Swapping the user model mid-project is a risky migration on a live DB |
| **`UserProfile` 1:1 model** (recommended) | No change to auth; same pattern as `Wallet`; easy to backfill | One extra join, mitigated by `select_related` |

**Memories: one text blob vs rows.** Rows (`MemoryItem`) give per-item type, delete, a 50-item cap, and a `source` column so future AI-made memories are distinguishable from user-made ones. A blob would be simpler but cannot support the requested list UI.

**How the prompt and memories reach the model.** Add a neutral `system` field on `ChatRequest`; each adapter maps it to its provider's native slot (OpenAI `system` message, Anthropic `system`, Gemini `systemInstruction`). Memories are appended to the same system text as a short "things to remember" block. Read at send time, so a change applies to existing chats immediately. **Unverified on the proxy**: capture real behaviour first (project rule), fall back to prepending to the first user message if a provider rejects it.

**Cost effect.** System text and memories are sent (and billed as input tokens) on every message. Mitigation: caps (prompt 4000 chars, memory 500 chars, 50 items), the reserve estimate counts the system text, and the page tells the user it counts toward usage.

**Default app.** One mapping `APP_HOME` from choice to URL name, used by a `LoginView` subclass. All three map to the chat home for now, so adding a real app later is a one-line change.

**Save behaviour.** Plain POST forms with redirects and a flash message: works without JavaScript and needs no new dependency. The toggle and segmented control submit on change/click.

## 4. Whether to build it
Yes. It is small relative to its value, reuses the existing design system, and the system-prompt integration is a real product feature. The riskiest part is the unverified provider behaviour, which is why the capture step comes before any adapter change.

## 5. Risks
- A provider may reject or ignore the system field (the proxy has rejected a standard parameter before). Mitigation: capture first; fallback path.
- Bigger inputs raise per-message cost. Mitigation above.
- The spec says the add form is "above" the list but the natural layout puts it below; we put it above so the empty-state text is true.
- Not a security boundary: the prompt is the user's own text for their own chats.

## 6. Out of scope
LLM-generated memories, editing items in place, real SimGen/Ask apps, changing username/password/display name here, per-conversation prompts.
