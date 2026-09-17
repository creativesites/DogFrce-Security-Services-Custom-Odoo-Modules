# Training Course: "Getting Live: Client Setup & Rostering"

> Status: Active · Created 2026-09-17 · Owner: Winston
> First real course for `security_training` (docs/deployguard/BUILD-STATUS-AND-
> PHASE-PLAN.md Phase 4.6). Seeded as data in
> `custom_addons/security_training/data/security_training_dogforce_course.xml`.

---

## 1. Why this course, and why this order

The founder's brief: DogForce needs to be rostering **as soon as possible**,
and the course has to fix the real gaps found in production this week
(docs/ROSTERING_SIMPLIFICATION_PLAN.md), not teach a generic ERP.

So the course follows the **critical path to a live roster**, in the order a
new client actually goes through it, and nothing else:

```
Set up a client  →  Check sites/shifts  →  Generate the roster
     →  Understand sign-offs  →  Post & review attendance
```

Everything in this course maps to a real screen that exists today, after
this session's fixes (the simplified Clients & Sites menu, the rewritten
onboarding wizard, the non-blocking sign-off sheet, the front-desk review
gate). It does not cover training authoring, competencies, or anything not
on that critical path — those can be a second course once this one is live.

**Audience:** everyone named in the six-role sign-off chain (Operations,
Front Desk, GM, HR, Finance, Director) — assign it to all of them. Each
"Do it" lesson works for whichever role is doing that step; the course
doesn't branch by role, the org does.

## 2. Course structure (as seeded)

| # | Section | Lessons | Deep link target |
|---|---|---|---|
| 1 | Before You Start | Welcome & What Changed · Your Role in the Process | — (orientation only) |
| 2 | Setting Up a New Client | Watch (video) · Do It | Onboarding wizard |
| 3 | Sites & Shift Requirements | Watch (video) · Do It | Client Sites list |
| 4 | Generating Your First Roster | Watch (video) · Do It | Client Sites → roster batch |
| 5 | Roster Sign-Offs | Watch (video) · Do It | Roster Sign-Offs |
| 6 | Daily Attendance & Front-Desk Review | Watch (video) · Do It | Posting Console |
| — | Assessment: "Getting Live: Check Your Understanding" | 5 questions, 80% pass mark, 3 attempts | — |

Each "Do It" lesson has a **"Try it in DogForce ERP"** button in the desktop
lesson player that deep-links straight to the real screen — this is the
"learn by doing" mechanism: the learner does the actual task in the actual
app, then returns to the lesson to mark it done. See §5 for why this is a
real deep link and not a simulated overlay.

## 3. What you still need to do before this goes live

1. **Record the five videos** using the shot lists in §4 below.
2. **Host each video** somewhere the desktop app's webview can play (a direct
   MP4 URL, or a YouTube/Vimeo unlisted embed — the lesson player renders
   the `video_url` field in an `<iframe>`, so an embeddable URL is required,
   not a bare file link on most hosts).
3. **Replace the placeholder URLs** in
   `security_training_dogforce_course.xml` (`REPLACE_WITH_HOSTED_VIDEO_URL_1`
   through `_5`) with the real ones, then upgrade the module
   (`-u security_training`) — remember this file is `noupdate="1"`, so a
   plain module upgrade won't touch already-loaded records; you'll need to
   either update the video URLs directly on the lesson records in the UI, or
   delete and re-run the data file once during setup.
4. **Assign the course** to a pilot group once videos are in, via Training →
   Assignments (or bulk-assign once that exists — today it's one at a time).
5. **Watch the first real learner go through it** and fix anything confusing
   before assigning it to everyone.

## 4. Video generation prompts (Gemini, 10-second clips)

You said you'll take real screenshots of the app and feed them in so the
generated clips match the actual UI — every prompt below is written for
that workflow: **each clip prompt assumes a specific real screenshot is
attached as the reference image**, and describes the motion/action to
animate on top of it, not a scene invented from scratch. Where a clip needs
a screenshot you haven't taken yet, that's named explicitly so you know what
to capture before generating.

**Continuity rules to keep all 12 clips feeling like one video, per video:**
- Same voice/caption style throughout (pick one: a narrator voiceover script
  is included per clip below; if you're doing on-screen captions instead,
  use the same caption line).
- Cursor moves smoothly and deliberately — no teleporting between clicks.
- Keep the DogForce toolbar and branding visible in every clip that shows
  the app (it's how learners recognise "I'm in the same place").
- End each clip on a settled frame (nothing mid-animation) so the join to
  the next clip doesn't jump.

Each video is 12 × 10-second clips = 120 seconds. Trim narration to fit;
the lines given are a starting point, not a fixed script.

---

### Video 1 — Setting Up a New Client (12 clips)

**Screenshots to capture first:** the Clients & Sites menu (mega menu open,
showing the "Set up a new client" button + four destination cards), and
each of the wizard's 5 steps with realistic sample data entered (a
believable Namibian client name, e.g. "Kalahari Mining Services").

| # | Prompt |
|---|---|
| 1 | Reference: the DogForce desktop app's Clients & Sites mega menu. Animate: a soft highlight/glow pulses once around the "Set up a new client" button to draw the eye, cursor moves toward it. Caption/voiceover: "Setting up a new client starts with one button." |
| 2 | Reference: same mega menu. Animate: cursor clicks the "Set up a new client" button; button shows a brief press state. Voiceover: "Click it, and the whole setup runs in five short steps." |
| 3 | Reference: Wizard Step 1 (Client) with the "Or a new client" fields empty. Animate: text types into "Company name" field character by character, then email and phone fields fill in. Voiceover: "Step one: tell it who the client is." |
| 4 | Reference: Wizard Step 1 with fields filled. Animate: cursor clicks "Continue"; a brief transition wipes to Step 2. Voiceover: "Continue moves you to sites." |
| 5 | Reference: Wizard Step 2 (Sites) empty grid. Animate: a new row appears, "Site Name" and "Code" fields type in realistic values (e.g. "Head Office", "HQ"). Voiceover: "Add one row per site the client needs guarded." |
| 6 | Reference: Wizard Step 2 with 2 rows filled. Animate: cursor clicks "Continue"; transition to Step 3. Voiceover: "You can always add more sites later." |
| 7 | Reference: Wizard Step 3 (Shift Requirements) empty grid. Animate: a row appears; the Site dropdown opens showing the site just created, then closes on selection. Voiceover: "Pick which site this shift covers." |
| 8 | Reference: Wizard Step 3, same row. Animate: Post Type dropdown opens (Static Guard, Gate, Patrol...) and "Static Guard" is selected; Shift dropdown opens and "Day Shift" is selected; Guards field types "2". Voiceover: "What kind of post, which shift, how many guards." |
| 9 | Reference: Wizard Step 3 with bill/pay rate columns visible, both at 0. Animate: a soft highlight appears under the rate columns with a small caption bubble. Voiceover: "Rates can stay at zero for now — you can still roster." |
| 10 | Reference: Wizard Step 4 (Billing). Animate: the Billing Mode dropdown opens, "Fixed Monthly Rate" is selected; Payment Term field shows "30". Voiceover: "Set how this client gets invoiced." |
| 11 | Reference: Wizard Step 5 (Review) showing the green "Ready to create" status and the summary table. Animate: cursor scrolls the summary table briefly, then hovers the "Create client" button. Voiceover: "Check the summary — this is everything about to be created." |
| 12 | Reference: same Step 5. Animate: cursor clicks "Create client"; screen transitions to the new client's record page. Voiceover: "One click, and the client, sites, shifts and billing all exist." |

---

### Video 2 — Sites, Posts & Shift Requirements (12 clips)

**Screenshots to capture first:** the Sites list view (grouped by client),
a client's own "Security Sites" tab, and a single site form's three tabs
(Posts & Shifts, Contacts & Location, Notes & Exclusions).

| # | Prompt |
|---|---|
| 1 | Reference: the Sites list grouped by client. Animate: cursor scrolls down slowly, showing several clients each with their sites nested underneath. Voiceover: "Every site, grouped by client, in one plain list." |
| 2 | Reference: same list. Animate: cursor clicks a client's group header to expand/collapse it. Voiceover: "Collapse a client you're not working on right now." |
| 3 | Reference: a client's record page with the "Sites" smart button visible in the top-right. Animate: a highlight pulses around the Sites button showing a count badge. Voiceover: "Or open the client directly." |
| 4 | Reference: same client page, Security Sites tab now open. Animate: cursor scrolls the tab showing sites, their contracts, and shift requirements listed inline. Voiceover: "Every site, every contract, every shift requirement — one screen." |
| 5 | Reference: a single site's form, Posts & Shifts tab. Animate: cursor clicks into the Posts & Shifts tab from another tab (transition). Voiceover: "Open a site, and here's what it needs guarded." |
| 6 | Reference: same tab, Posts sub-list. Animate: cursor adds a new post row, Post Type dropdown opens showing all five types. Voiceover: "Static Guard, Gate, Patrol, Control Room, or Site Supervisor." |
| 7 | Reference: same tab, Shift Requirements sub-list. Animate: cursor adds a row, Shift Template dropdown opens (Day 06-18, Night 18-06, Day 08-16, Relief). Voiceover: "Pick from the standard shift templates — no need to build one from scratch." |
| 8 | Reference: Contacts & Location tab. Animate: transition into this tab; Contact Name and Phone fields highlighted briefly. Voiceover: "Site contact details live here." |
| 9 | Reference: same tab, GPS section marked "(optional)". Animate: a soft highlight and a small caption bubble over the GPS fields. Voiceover: "GPS geofencing is optional — never required to save a site." |
| 10 | Reference: Notes & Exclusions tab. Animate: transition into this tab; Operational Notes field shows placeholder text typing in. Voiceover: "Special instructions for the site go here." |
| 11 | Reference: same tab, Guard Exclusions sub-list. Animate: cursor adds a row, Employee dropdown opens. Voiceover: "If a client asks for a guard removed, add them here — rostering blocks that guard from this site automatically." |
| 12 | Reference: back to the Sites list view, zoomed out. Animate: cursor hovers the whole list calmly, settling. Voiceover: "That's the whole picture — clients, sites, shifts, all connected." |

---

### Video 3 — Generating a Roster (12 clips)

**Screenshots to capture first:** the Rostering menu, a roster batch form
in Draft state, the same batch after "Generate Roster Slots", the slot grid
with some unassigned (red) slots, and the batch after "Confirm Roster."

| # | Prompt |
|---|---|
| 1 | Reference: the Rostering menu open. Animate: cursor moves down the menu items settling on the roster batch action. Voiceover: "Once a client's sites and shifts exist, the roster is next." |
| 2 | Reference: a roster batch form, Draft state, statusbar showing "Draft" highlighted. Animate: cursor hovers the date range fields. Voiceover: "Every roster is a batch — a client or site, and a date range." |
| 3 | Reference: same form. Animate: cursor clicks "Generate Roster Slots" button; a brief loading state, then the slot list populates below. Voiceover: "Generate Roster Slots reads every active shift requirement..." |
| 4 | Reference: the generated slot list, several rows, some with an employee assigned and some blank (red decoration). Animate: cursor scrolls the slot list slowly. Voiceover: "...and creates one slot per guard, per shift, per day." |
| 5 | Reference: same list, zoomed on an unassigned red row. Animate: a highlight pulses on the red row. Voiceover: "Unassigned slots show in red — you can't miss them." |
| 6 | Reference: same form, header buttons visible including "Auto-Fill Open Slots". Animate: cursor clicks it; loading state; red rows turn to assigned. Voiceover: "Auto-Fill Open Slots assigns the best eligible guard automatically." |
| 7 | Reference: the slot list after auto-fill, a row's Employee dropdown open showing manual override in progress. Animate: dropdown opens, a different guard is selected. Voiceover: "You can still assign by hand wherever you want to." |
| 8 | Reference: same form, statusbar now on "Generated". Animate: cursor moves toward the "Confirm Roster" button. Voiceover: "Once you're happy with the assignments..." |
| 9 | Reference: same form. Animate: cursor clicks "Confirm Roster"; statusbar animates from "Generated" to "Confirmed". Voiceover: "...Confirm Roster. This roster is now live." |
| 10 | Reference: the Roster Sign-Offs smart button/panel now visible on the confirmed batch. Animate: a highlight pulses on the sign-off summary text. Voiceover: "Guards can be posted right away — no sign-off needed first." |
| 11 | Reference: same confirmed batch form, scrolled to show it fully. Animate: cursor scrolls up and down once, calm. Voiceover: "The sign-off sheet appears now too — more on that next." |
| 12 | Reference: same screen, settled. Animate: gentle zoom out on the whole confirmed batch. Voiceover: "That's a roster, start to finish." |

---

### Video 4 — Understanding Sign-Offs (12 clips)

**Screenshots to capture first:** the Roster Sign-Offs list (grouped by
batch, filtered to "Awaiting sign-off"), a single batch's sign-off rows
showing all five roles pending, one row after signing, and one row flagged
with a comment.

| # | Prompt |
|---|---|
| 1 | Reference: the Roster Sign-Offs list, several batches each with pending rows. Animate: cursor scrolls the list slowly. Voiceover: "Every generated roster gets a sign-off sheet — five roles, one row each." |
| 2 | Reference: one batch's five sign-off rows, all "Pending" badges. Animate: highlight moves across each role name in sequence (Front Desk, GM, HR, Finance, Director). Voiceover: "Front Desk, General Manager, HR, Finance, and the Director." |
| 3 | Reference: same rows. Animate: a caption bubble appears over the whole panel. Voiceover: "None of this stops the roster. Guards are already working." |
| 4 | Reference: a single row for the viewer's own role, "Sign off" button visible. Animate: cursor hovers the Sign off button. Voiceover: "If your role is on the list, this is your job." |
| 5 | Reference: same row, comment field empty. Animate: cursor types a short comment, e.g. "Checked, looks correct." Voiceover: "Add a comment if it's useful — it's optional." |
| 6 | Reference: same row. Animate: cursor clicks "Sign off"; badge animates from "Pending" to "Signed off" (green). Voiceover: "Click Sign off, and it's recorded — who, and when." |
| 7 | Reference: a different row, "Flag" button visible. Animate: cursor hovers Flag. Voiceover: "If something's actually wrong with the roster..." |
| 8 | Reference: same row, a comment field now required/highlighted. Animate: cursor types a reason, e.g. "Night shift looks short-staffed at Site B." Voiceover: "...Flag it, with a reason — that part's required." |
| 9 | Reference: same row after flagging, badge red "Flagged". Animate: badge animates to red. Voiceover: "The roster keeps running. The flag is what gets followed up. This is accountability, not a roadblock." |
| 10 | Reference: the batch's overall sign-off summary line (e.g. "Awaiting HR, Finance"). Animate: highlight on the summary text. Voiceover: "The summary always shows exactly who it's still waiting on." |
| 11 | Reference: a batch where all five rows show "Signed off". Animate: cursor scrolls down the fully-signed list. Voiceover: "Once everyone's signed, the sheet is simply complete — nothing else happens automatically, and nothing needed to." |
| 12 | Reference: settled view of the sign-off list. Animate: gentle zoom out. Voiceover: "Sign when you've checked. Flag when something's wrong. Either way, the roster doesn't wait." |

---

### Video 5 — Posting & Reviewing Attendance (12 clips)

**Screenshots to capture first:** the Posting Console with a site/date
selected and guards showing "Not Marked", the same console after marking
everyone, the "Review & Validate" button, and the console showing a
"Reviewed" state badge.

| # | Prompt |
|---|---|
| 1 | Reference: the Posting Console, site and date pickers at top, empty guard list below. Animate: date picker opens, today's date is selected. Voiceover: "Every day starts with the Posting Console." |
| 2 | Reference: same console, guard list populated with "Not Marked" status for each row. Animate: cursor scrolls the guard list. Voiceover: "Every guard scheduled today shows up here automatically." |
| 3 | Reference: same list, one row's presence dropdown open (Present/Absent/AWOL). Animate: dropdown opens, "Present" selected. Voiceover: "Mark each guard: present, absent, or AWOL." |
| 4 | Reference: same list, several rows now marked, mix of statuses. Animate: cursor works down the list marking 2-3 more rows quickly. Voiceover: "Work down the list for the whole site." |
| 5 | Reference: same console, "Save Changes" button with a dirty-count badge. Animate: cursor clicks Save; badge clears, brief success toast. Voiceover: "Save, and the batch is captured." |
| 6 | Reference: same console, status badge now shows "Captured". Animate: highlight on the status badge. Voiceover: "That's Operations' part done for the day." |
| 7 | Reference: same console, opened by a different (Front Desk) session, same site/date. Animate: transition to Front Desk's view of the same captured batch. Voiceover: "Front Desk's job starts right here." |
| 8 | Reference: same console, guard list showing the same marks Operations entered. Animate: cursor reviews the list, hovering each row briefly. Voiceover: "Check what was posted against what actually happened." |
| 9 | Reference: same console, "Review & Validate" button visible. Animate: cursor hovers, then clicks the button. Voiceover: "Review & Validate — this is Front Desk's sign-off on the day." |
| 10 | Reference: same console, status badge animates to "Reviewed". Animate: badge color/label change. Voiceover: "The batch is now reviewed, not just captured." |
| 11 | Reference: an attempted review by the same user who captured it, showing the refusal message. Animate: click on Review & Validate, an error toast appears with the real refusal text. Voiceover: "One rule: whoever captures a posting can't also review it themselves." |
| 12 | Reference: settled view of a Reviewed batch. Animate: gentle zoom out. Voiceover: "Post it, then let someone else check it. That's the whole handoff." |

---

## 5. Why "learn by doing" is a real deep link, not a fake overlay

The desktop app's Odoo webview deliberately has **zero IPC and no injected
script** (`desktop/DEVIATIONS.md`, `capabilities/main.json`) — a real
security boundary that's been maintained carefully through this whole
build. A coach-mark drawn on top of Odoo's own DOM would require either
scripting that webview (breaking the boundary) or guessing fixed screen
coordinates (fragile, breaks on any Odoo UI change or window resize).

Instead, each "Do It" lesson's **"Try it in DogForce ERP"** button calls the
same `navigate_odoo` Tauri command the toolbar already uses, sending the
live Odoo webview straight to the real screen
(`security_training_course.py`'s `deep_link_path` field, one per lesson).
The learner does the actual task in the actual app — not a simulation —
then returns to the lesson (via the existing app-view toggle) to mark it
done. This is genuine learn-by-doing, built on infrastructure that already
existed rather than a new, riskier mechanism.

## 6. AI assist — explicit product decision

The lesson player includes an optional "Ask AI about this lesson" panel
(`security.training.lesson.ask_ai`, Gemini via the existing
`security_ai_engine` provider). This is a deliberate exception to
[28-mvp-scope.md](deployguard/28-mvp-scope.md) §3.1's "no AI-generated text
anywhere in the MVP" guardrail, approved explicitly by Winston (2026-09-17)
for the training assistant specifically — not a reopening of that scope
guard elsewhere. It answers only from the lesson's own text, never grades
anything (assessment scoring stays 100% deterministic), and fails with a
plain message rather than crashing if `security_ai_engine` isn't installed
or has no Gemini key configured.

## 7. Change log

| Date | Change |
|---|---|
| 2026-09-17 | Created. Course seeded, lesson player built with deep-link "learn by doing" and an optional AI assist panel. Video content not yet recorded — placeholder URLs in the seed data. |
