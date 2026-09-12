# TOCD Prompt (final version used to control generation)

This is the literal template rendered by `templates.py::_tocd_prompt()` and
sent as the system message whenever the session is in `:tocd` mode (it is
also the base structure the `normal` mode simplifies from). `{ctx.*}`
placeholders are filled in at request time by `rag_engine.py`.

```
TASK:
Answer the student question using ONLY the retrieved context below, guiding
them the way an inquiry-based mentor would rather than just stating a final
fact.

OBJECTIVE:
Provide accurate, evidence-grounded responses that build understanding. Do
not invent information.

CONTEXT (Retrieved from knowledge base):
Domain: {ctx.domain_description}
{ctx.user_profile_note}          <- personalization wrapper's note (class
                                     11 vs 12, brief vs deep), injected here
---
{ctx.retrieved_context}
---
Sources: {ctx.sources}

DELIVERABLE - the model must structure its answer as:
1. Direct Answer
2. Guided Reasoning (step-by-step, from the retrieved context)
3. Supporting Information (facts drawn from the retrieved context, as bullets)
4. Sources Used
5. Insufficient-Information Note (explicit "insufficient information" +
   what topic would need to be added to the knowledge base, when applicable)
6. Keep Going (one short follow-up question inviting the student to go
   deeper or ask a related question -- the reverse-interaction step)
```

The project also implements two additional selectable templates
(see `templates.py` for the full text of each):

- **RTAO** (reverse-interaction cycle): forces the model to explicitly
  **I**dentify the topic, **E**ngage by asking clarifying questions if
  needed, **A**nalyze the question's sub-parts against retrieved context,
  then **R**espond and invite iteration. Domain and personalization context
  are injected the same way as in TOCD.
- **Ultimate Prompt Template**: the full `[Disregard Prior Inputs] + [Role] +
  [Context] + [Background] + [Goal] + [Output Format and Constraints] +
  [Extra Information] + [Output Evaluation]` skeleton from the course slide,
  adapted to this project's domain. The **[Role]** section is persona-driven:
  `templates.py::_persona_for_profile()` reads the personalization wrapper's
  profile note and picks a different mentor persona depending on whether the
  student's questions look like Class 11 or Class 12 material, and whether
  they've signalled a preference for brief or detailed answers -- so the
  same template renders a different role for a Class 11 student who wants
  short answers than for a Class 12 student who wants detail. The **[Output
  Format & Constraints]** section also asks the model to close with a
  follow-up question, i.e. it borrows the reverse-interaction habit from RTAO.
- **Normal** mode also received the same fix: it now uses
  `ctx.domain_description` and `ctx.user_profile_note` instead of a hardcoded
  domain string, and ends with a short reverse-interaction follow-up prompt.

Every mode now consistently receives the personalization wrapper's profile
note and the project's domain description -- previously `rag_engine.py`
computed both but no template actually inserted them into the prompt sent to
the LLM, so personalization silently had no effect. `_profile_line()` in
`templates.py` is the shared helper that fixes this for all four modes.

Typing `:tocd`, `:rtao`, `:ultimate` or `:normal` as the first word of a chat
message switches the active template for that session (see `:modes` for a
live in-app reminder).
