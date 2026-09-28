# Daily Attendance: media generation pack

For Gemini video and image generation. Each video is built from **10-second
clips** that an editor joins with straight cuts into one lesson video. Every
clip prompt below is complete; you should not need to rewrite it. Attach the
named screenshot as the reference image for every clip that shows software.

Lesson ↔ video mapping: [`README.md`](./README.md).

---

## 1. Continuity bible (applies to every clip)

Paste this block at the top of **every** generation request, before the
clip's own prompt.

```
CONTINUITY BIBLE: DogForce Daily Attendance training series

WORLD: A small, real, working security-company office in Lusaka, Zambia. White
painted walls, one wall with a whiteboard listing client sites in marker, a
wall calendar, a wooden desk per person, black office chairs, a two-way radio
charger on a shelf, a window with half-open white blinds. Tidy but lived-in. No
futuristic elements, no glowing holograms, no floating UI.

TIME AND LIGHT: Weekday morning, about 09:30. Soft natural daylight from the
window (camera left), plus neutral overhead office light. Warm-neutral colour,
realistic exposure. The light stays the same in every clip.

PEOPLE (the same actors and wardrobe in every clip they appear in):
- GRACE, Operations Supervisor: Zambian woman, early 30s, short neat braids
  tied back, navy polo shirt with a small white "DogForce" text logo on the
  left chest, black trousers, silver wristwatch on left wrist. Calm and
  competent.
- JOSEPH, Admin: Zambian man, late 20s, short hair, light-blue long-sleeve
  shirt, dark tie, reading glasses he puts on to check the screen.
- RUTH, HR officer: Zambian woman, 40s, shoulder-length relaxed hair, maroon
  blouse, cardigan over the chair back.
- THE GENERAL MANAGER: Zambian man, 50s, grey at the temples, white shirt,
  no tie, sleeves rolled once.

DEVICES: Each person uses a Windows laptop (dark grey, 14-inch) connected to a
24-inch monitor. The monitor shows the software exactly as in the supplied
screenshot. Wired mouse. No phones on screen.

SOFTWARE ON SCREEN: The monitor content is the supplied screenshot, shown
flat, sharp and readable, at the monitor's real proportions. Keep its layout,
colours, fonts, buttons and text exactly. Do not invent other windows, apps,
dashboards or data. Do not stylise it. It is DogForce's real ERP (Odoo) with
the DeployGuard panel.

CAMERA LANGUAGE: Tripod or very slow dolly only. Eye level. 35 mm lens look,
shallow but not extreme depth of field. Screen close-ups are straight-on,
monitor filling about 80 % of the frame, no keystone distortion. No handheld
shake, no whip pans, no zoom-bursts, no Dutch angles.

VISUAL TREATMENT: Natural, documentary, calm. No colour grading gimmicks, no
lens flares, no vignettes, no film grain overlays, no text overlays unless the
clip specifies one.

AUDIO BED: Quiet office room tone only (faint distant traffic through the
window, soft keyboard clicks when someone types). No music anywhere. Narration
is recorded separately and laid over the joined video.

CLIP JOINS: Every clip starts already in motion (mid-action, steady framing)
and ends on a held, steady frame for the last ~0.5 s. No fades, no
transitions, no title animations, no stings, no sudden sounds at the start or
end.
```

**Narration** is one continuous voice-over recorded after the clips are
joined. Each line below is written to fit inside its clip, so a clip
boundary never splits a sentence. Voice: warm, unhurried, clear Zambian
English, as a friendly senior colleague would explain it. Not a
salesperson.

---

## 2. Screenshots to capture (from staging, never production)

Use a staging database with test sites and test guard names. Capture at 1920
× 1080, Windows display scaling 100 %, DeployGuard window maximised.

| ID | Screen | How to get there | Must show |
|---|---|---|---|
| SS-01 | DeployGuard **Today** for the Operations Supervisor | Sign in as the Ops Supervisor test user; DeployGuard opens on Today | A "Register attendance · ABC Mall" card with its why-text, "Due 10:00", **Guide me** and **I know how** buttons |
| SS-02 | **Guide dock** step 1 | Press Guide me | ERP on the left with the highlight ring on **Workforce**; guide panel on the right: "Step 1 of 3 · Open the Posting Console" |
| SS-03 | **Posting Console**, no sheet yet | Workforce → Posting Console, choose ABC Mall and today | "No Posting Sheet Found" and the **Create Batch & Generate from Roster** button highlighted; guide at Step 2 |
| SS-04 | **Posting Console**, guards listed | Press Create Batch & Generate from Roster | 3–5 guard cards all "Not Marked", presence buttons visible; guide at Step 3 |
| SS-05 | **Posting Console**, marked, unsaved | Mark guards (one Absent, rest Present) | Present/Absent buttons selected, **Save Changes** with orange unsaved count |
| SS-06 | **Team Today** (GM) | Sign in as the GM test user → Team Today | Pipeline grid: ABC Mall row with Register "Done", Confirm "To do", Verify "Waiting" |
| SS-07 | **Guide dock**, finished | Save in the console | Guide panel "Done", ERP showing the saved sheet |
| SS-08 | **Today** for Admin | Sign in as the Admin test user | "Confirm attendance · ABC Mall", ready (after SS-07) |
| SS-09 | **Posting Console**, captured, for Admin | Admin opens ABC Mall / today | Status badge "Captured", **Review & Validate** button highlighted by the guide |
| SS-10 | **Posting Sheets** form, reviewed | Sign in as HR → Workforce → Posting Sheets → open ABC Mall | Statusbar at Reviewed, **Verify & lock** button highlighted |

---

## 3. Video DA1: "Why does today's attendance have to be done today?" (4 clips, ~40 s)

### DA1-01

```
CLIP ID: DA1-01
COURSE: Daily Attendance: Register, Confirm, Verify
LESSON: Why does today's attendance have to be done today?
SEQUENCE: 1 of 4
DURATION: 10 seconds
PREVIOUS CLIP: none (opening clip)
NEXT CLIP: DA1-02 (screen close-up of the same monitor)

REFERENCE: Use supplied screenshot SS-01 as the authoritative UI reference for the monitor content.

SCENE: Grace arrives at her desk in the DogForce office in the morning and sits down in front of her monitor, which already shows DeployGuard's Today screen.

SUBJECT: GRACE (see continuity bible).

ACTION: Clip opens with Grace already lowering herself into her chair, coffee mug in her right hand. She places the mug down to the right of the keyboard, rests her hand on the mouse, and looks at the screen, reading, with a small nod. She does not speak.

CAMERA: Static tripod, medium shot from her front-left at eye level, showing Grace from the waist up and the monitor on the right third of the frame, screen content readable but not yet the focus. A very slow push-in of about 5 % across the 10 seconds.

LIGHTING: Morning daylight from the window at camera left, soft; neutral overhead office light.

ENVIRONMENT: Her desk, whiteboard with client site names slightly out of focus behind her, radio charger on the shelf.

UI FIDELITY: The monitor shows SS-01 exactly: DeployGuard Today with the "Register attendance · ABC Mall" card. Keep layout, colours and text; no extra windows.

CONTINUITY: Grace's wardrobe, watch, braids and the mug stay exactly as described; the mug remains on the desk in later clips.

AUDIO: Office room tone, the soft sound of the mug being set down. No music, no speech.

ENDING: Hold on Grace looking at the screen, steady framing, for the last half second.

NEGATIVE CONSTRAINTS: No holograms, no floating UI, no glowing screen, no text overlays, no logos other than the small shirt logo, no music, no dramatic lighting, no camera shake, no other people.

GENERATION PROMPT: Realistic documentary-style office footage, 10 seconds, 35 mm look. A Zambian woman in her early 30s with short neat braids tied back, wearing a navy polo shirt with a small white "DogForce" text logo and a silver wristwatch, sits down at a wooden desk in a small white-walled security-company office in Lusaka at 9:30 in the morning. She sets a coffee mug down beside the keyboard, rests her hand on the wired mouse and reads the 24-inch monitor with a small nod. The monitor displays the supplied screenshot SS-01 exactly, flat and sharp: a business web application showing a list titled with a task card "Register attendance · ABC Mall". Soft daylight from a window with half-open white blinds on the left, whiteboard with handwritten site names blurred behind her. Static tripod medium shot at eye level with a barely perceptible slow push-in. Quiet room tone, no music, no text overlays, calm and natural. Ends on a steady held frame.
```

**Narration:** "Every morning, today's attendance starts here, in DeployGuard."

### DA1-02

```
CLIP ID: DA1-02
COURSE: Daily Attendance: Register, Confirm, Verify
LESSON: Why does today's attendance have to be done today?
SEQUENCE: 2 of 4
DURATION: 10 seconds
PREVIOUS CLIP: DA1-01 (Grace sitting down, monitor in frame)
NEXT CLIP: DA1-03 (wide shot of the office)

REFERENCE: Use supplied screenshot SS-01 as the authoritative UI reference.

SCENE: Close-up of Grace's monitor showing her Today card.

SUBJECT: The monitor screen; Grace's right hand on the mouse at the bottom edge of frame.

ACTION: Clip opens already on the screen. The mouse pointer rests near the "Register attendance · ABC Mall" card, then moves slowly across the "why it matters" sentence as if she is reading it, and stops beside it.

CAMERA: Straight-on screen close-up, monitor filling about 80 % of the frame, no keystone. Locked off; no movement.

LIGHTING: Same daylight; faint window reflection on the matte screen edge only, never over the text.

ENVIRONMENT: Monitor bezel and the top of the keyboard visible at the bottom edge.

UI FIDELITY: SS-01 exactly. The card text reads "Payroll, client billing and AWOL follow-up are worked out from this register…" Do not change any wording, colour or layout.

CONTINUITY: Same monitor, same desk, same watch on Grace's left wrist if her hand enters the frame.

AUDIO: Room tone; one soft mouse movement sound. No music.

ENDING: Pointer at rest beside the sentence, steady hold.

NEGATIVE CONSTRAINTS: No UI animation that doesn't exist, no highlighted glows, no zooming into the UI, no invented buttons, no text overlays.

GENERATION PROMPT: Straight-on close-up of a 24-inch office monitor filling most of the frame, showing the supplied screenshot SS-01 exactly as a flat, sharp, readable screen: a task card "Register attendance · ABC Mall" with a short sentence underneath explaining that payroll and billing are worked out from this register. A mouse pointer slowly moves along that sentence and stops. A woman's hand with a silver wristwatch rests on a wired mouse at the lower edge. Soft natural daylight, no reflections over text, locked-off camera, realistic, 10 seconds, quiet room tone, no music, no overlays, ends on a steady frame.
```

**Narration:** "Payroll, client billing and AWOL follow-up are all worked out from this one register."

### DA1-03

```
CLIP ID: DA1-03
COURSE: Daily Attendance: Register, Confirm, Verify
LESSON: Why does today's attendance have to be done today?
SEQUENCE: 3 of 4
DURATION: 10 seconds
PREVIOUS CLIP: DA1-02 (monitor close-up)
NEXT CLIP: DA1-04 (the General Manager at his laptop)

REFERENCE: No software detail is readable in this clip; monitors may show SS-01, SS-09 and SS-10 small in the background.

SCENE: Wide shot of the office showing the three people in the attendance chain at their desks.

SUBJECT: GRACE (foreground left desk), JOSEPH (middle desk, puts on reading glasses), RUTH (right desk, typing).

ACTION: Clip opens mid-activity: Grace clicks her mouse; Joseph puts on his reading glasses and leans toward his screen; Ruth types, then glances up and across the room with a brief friendly look. Normal, unhurried work.

CAMERA: Static wide shot from the room's back corner at standing eye level, all three desks visible, slow lateral dolly of about 30 cm left-to-right across the clip.

LIGHTING: Same morning daylight and overhead light.

ENVIRONMENT: Whiteboard, wall calendar, radio charger, window blinds, all consistent with the bible.

UI FIDELITY: Screens are small in frame; if legible they must match the supplied screenshots, otherwise keep them softly out of focus rather than invent content.

CONTINUITY: Grace's mug on her desk from DA1-01; all wardrobe exactly per the bible.

AUDIO: Room tone, light keyboard clicks from Ruth. No music, no dialogue.

ENDING: Hold steady on the three at work.

NEGATIVE CONSTRAINTS: No extra people, no posing to camera, no exaggerated smiles, no text overlays, no music.

GENERATION PROMPT: Realistic documentary wide shot, 10 seconds, of a small white-walled security-company office in Lusaka on a weekday morning. Three colleagues work at wooden desks with laptops and monitors: in the foreground a woman in a navy DogForce polo clicks her mouse; at the middle desk a young man in a light-blue shirt and dark tie puts on reading glasses and leans toward his screen; at the right desk a woman in her 40s in a maroon blouse types and glances up briefly. Whiteboard with site names, wall calendar, radio charger on a shelf, window with half-open white blinds, soft daylight. Very slow smooth lateral dolly, eye level, natural colours, quiet room tone and soft typing, no music, no text. Ends on a steady frame.
```

**Narration:** "Grace registers it. Joseph confirms it. Ruth verifies it, so payroll can use it."

### DA1-04

```
CLIP ID: DA1-04
COURSE: Daily Attendance: Register, Confirm, Verify
LESSON: Why does today's attendance have to be done today?
SEQUENCE: 4 of 4
DURATION: 10 seconds
PREVIOUS CLIP: DA1-03 (wide shot of the three at work)
NEXT CLIP: none (end of lesson video)

REFERENCE: Use supplied screenshot SS-06 as the authoritative UI reference.

SCENE: The General Manager at his laptop checking Team Today.

SUBJECT: THE GENERAL MANAGER (per bible).

ACTION: Clip opens with him already looking at his screen, then scrolling once with the mouse wheel and giving a satisfied small nod. He does not speak.

CAMERA: Over-the-shoulder from his right, monitor readable on the left two-thirds of the frame, slow push-in about 5 %.

LIGHTING: Same office daylight.

ENVIRONMENT: His desk in the same office, near the window.

UI FIDELITY: SS-06 exactly: the Team Today grid with ABC Mall's row showing Register "Done", Confirm "To do", Verify "Waiting". Do not invent numbers or charts.

CONTINUITY: GM wardrobe per bible.

AUDIO: Room tone, one mouse-wheel scroll. No music.

ENDING: Hold on the screen and his shoulder, steady.

NEGATIVE CONSTRAINTS: No charts or KPIs that aren't in SS-06, no glowing dashboards, no text overlays, no music sting, no fade out.

GENERATION PROMPT: Realistic over-the-shoulder shot, 10 seconds, of a Zambian man in his 50s with grey temples and a white shirt with sleeves rolled once, looking at a monitor in a small white-walled office in Lusaka in the morning. The monitor shows the supplied screenshot SS-06 exactly, sharp and readable: a simple table of client sites against three steps ("Register attendance", "Confirm attendance", "Verify attendance") with status labels. He scrolls once with the mouse wheel and gives a small satisfied nod. Soft daylight, slow push-in, natural colours, quiet room tone, no music, no overlays. Ends on a steady held frame with no fade.
```

**Narration:** "And the manager can see where every site has got to, without having to ask anyone."

---

## 4. Video DA2: "How do I register a site's attendance?" (6 clips, ~60 s)

### DA2-01

```
CLIP ID: DA2-01
COURSE: Daily Attendance: Register, Confirm, Verify
LESSON: How do I register a site's attendance?
SEQUENCE: 1 of 6
DURATION: 10 seconds
PREVIOUS CLIP: none (opening clip)
NEXT CLIP: DA2-02 (screen close-up, guide dock)

REFERENCE: Use supplied screenshot SS-01 as the authoritative UI reference.

SCENE: Grace at her desk about to start registering attendance for ABC Mall.

SUBJECT: GRACE.

ACTION: Clip opens with Grace already seated, reading the Today card. She moves the mouse to the "Guide me" button on the card and clicks once, calmly.

CAMERA: Medium shot from her front-left at eye level (same framing as DA1-01), monitor on the right third, readable. Locked off.

LIGHTING: Morning daylight from the left, neutral overhead light.

ENVIRONMENT: Same desk, mug beside keyboard, whiteboard behind.

UI FIDELITY: SS-01 exactly, with the "Guide me" button visible on the ABC Mall card.

CONTINUITY: Identical wardrobe, watch, mug position to DA1-01.

AUDIO: Room tone and a single soft mouse click. No music.

ENDING: Steady hold just after the click, before any screen change.

NEGATIVE CONSTRAINTS: No screen transitions, no glowing button, no text overlays, no music, no camera movement.

GENERATION PROMPT: Realistic medium shot, 10 seconds, locked-off at eye level: a Zambian woman in her early 30s in a navy DogForce polo with a silver wristwatch, seated at a wooden desk in a small bright Lusaka office, reads her monitor, moves the wired mouse and clicks a button labelled "Guide me" on a task card. The monitor shows the supplied screenshot SS-01 exactly, flat and readable. Coffee mug beside the keyboard, whiteboard with site names softly blurred behind, daylight from a window with half-open blinds on the left. Quiet room tone, one soft click, no music, no overlays, ends on a steady frame.
```

**Narration:** "To register a site, open your task on Today and press Guide me."

### DA2-02

```
CLIP ID: DA2-02
COURSE: Daily Attendance: Register, Confirm, Verify
LESSON: How do I register a site's attendance?
SEQUENCE: 2 of 6
DURATION: 10 seconds
PREVIOUS CLIP: DA2-01 (Grace clicks Guide me)
NEXT CLIP: DA2-03 (Posting Console, no sheet yet)

REFERENCE: Use supplied screenshot SS-02 as the authoritative UI reference.

SCENE: Straight-on close-up of the monitor: the ERP on the left with a highlight ring around the Workforce menu, the DeployGuard guide panel on the right.

SUBJECT: The monitor screen; mouse pointer.

ACTION: Clip opens already on SS-02. The mouse pointer moves from the guide panel on the right across to the highlighted "Workforce" menu at the top left and hovers over it.

CAMERA: Straight-on screen close-up, monitor ~80 % of frame, locked off.

LIGHTING: Same daylight, no reflections across the text.

ENVIRONMENT: Monitor bezel visible.

UI FIDELITY: SS-02 exactly: the blue highlight ring around "Workforce", the guide panel text "Step 1 of 3 · Open the Posting Console". Do not animate the ring beyond a subtle steady glow if present in the screenshot.

CONTINUITY: Same monitor as DA1-02.

AUDIO: Room tone, faint mouse movement. No music.

ENDING: Pointer hovering on "Workforce", steady.

NEGATIVE CONSTRAINTS: No invented menus, no extra highlight effects, no zoom, no overlays.

GENERATION PROMPT: Straight-on close-up of a monitor showing the supplied screenshot SS-02 exactly: a business application on the left with a thin blue rectangle highlighting a top menu item "Workforce", and a narrow white panel on the right titled "Guide" reading "Step 1 of 3 · Open the Posting Console". A mouse pointer glides from the right panel to hover over "Workforce". Flat, sharp, readable screen, locked-off camera, soft office daylight, quiet room tone, no music, no overlays, 10 seconds, ends on a steady frame.
```

**Narration:** "DeployGuard opens the ERP with a guide beside it, and shows you where to go: Workforce, then Posting Console."

### DA2-03

```
CLIP ID: DA2-03
COURSE: Daily Attendance: Register, Confirm, Verify
LESSON: How do I register a site's attendance?
SEQUENCE: 3 of 6
DURATION: 10 seconds
PREVIOUS CLIP: DA2-02 (pointer on Workforce)
NEXT CLIP: DA2-04 (guards listed)

REFERENCE: Use supplied screenshot SS-03 as the authoritative UI reference.

SCENE: Close-up of the Posting Console with ABC Mall and today chosen and no sheet yet.

SUBJECT: Monitor screen; pointer.

ACTION: Clip opens on SS-03. The pointer moves to the highlighted "Create Batch & Generate from Roster" button and rests on it.

CAMERA: Straight-on screen close-up, locked off.

LIGHTING: Same.

ENVIRONMENT: Monitor bezel.

UI FIDELITY: SS-03 exactly, including the date field, the "ABC Mall" site selection, "No Posting Sheet Found" text and the button label.

CONTINUITY: Same monitor.

AUDIO: Room tone. No music.

ENDING: Pointer resting on the button, steady.

NEGATIVE CONSTRAINTS: No invented data, no transitions, no overlays.

GENERATION PROMPT: Straight-on close-up of a monitor showing the supplied screenshot SS-03 exactly: a dark-toolbar "Posting Console" screen with a date field, a site dropdown set to "ABC Mall", the message "No Posting Sheet Found" and a button "Create Batch & Generate from Roster" outlined by a thin blue highlight. A mouse pointer moves onto that button and rests. Flat, sharp, readable, locked-off, soft daylight, room tone only, no music, no overlays, 10 seconds, ends steady.
```

**Narration:** "Choose the site and today's date, then create the sheet from the roster."

### DA2-04

```
CLIP ID: DA2-04
COURSE: Daily Attendance: Register, Confirm, Verify
LESSON: How do I register a site's attendance?
SEQUENCE: 4 of 6
DURATION: 10 seconds
PREVIOUS CLIP: DA2-03 (pointer on Create Batch)
NEXT CLIP: DA2-05 (marking guards)

REFERENCE: Use supplied screenshot SS-04 as the authoritative UI reference.

SCENE: Close-up of the Posting Console now listing the rostered guards, all "Not Marked".

SUBJECT: Monitor screen.

ACTION: Clip opens on SS-04. The pointer slowly moves down the column of guard cards without clicking, as if counting them.

CAMERA: Straight-on close-up, locked off.

LIGHTING: Same.

ENVIRONMENT: Monitor bezel.

UI FIDELITY: SS-04 exactly; guard names are staging test names; each card shows "Not Marked" and Present / Absent / AWOL buttons.

CONTINUITY: Same monitor.

AUDIO: Room tone. No music.

ENDING: Pointer at the last card, steady.

NEGATIVE CONSTRAINTS: No real names beyond those in the screenshot, no invented cards, no overlays.

GENERATION PROMPT: Straight-on close-up of a monitor showing the supplied screenshot SS-04 exactly: a grid of three to five guard cards, each marked "Not Marked" with three buttons "Present", "Absent", "AWOL". A mouse pointer moves slowly down the cards without clicking. Flat, sharp, readable screen, locked-off camera, soft office daylight, room tone only, no music, no overlays, 10 seconds, ends on a steady frame.
```

**Narration:** "Everyone rostered at that site today is already listed. Nobody is added by hand, and nobody is forgotten."

### DA2-05

```
CLIP ID: DA2-05
COURSE: Daily Attendance: Register, Confirm, Verify
LESSON: How do I register a site's attendance?
SEQUENCE: 5 of 6
DURATION: 10 seconds
PREVIOUS CLIP: DA2-04 (guards listed)
NEXT CLIP: DA2-06 (save and done)

REFERENCE: Use supplied screenshot SS-05 as the authoritative UI reference for the end state; SS-04 for the start.

SCENE: Grace marks each guard.

SUBJECT: GRACE's hand and the monitor.

ACTION: Clip opens mid-action on an over-the-shoulder view. Grace clicks "Present" on the first card, "Present" on the second, then pauses, glances at a paper call-in sheet on her desk, and clicks "Absent" on the third. The screen ends matching SS-05.

CAMERA: Over-the-shoulder from her right, monitor readable, locked off.

LIGHTING: Same.

ENVIRONMENT: A handwritten call-in sheet on a clipboard beside the keyboard.

UI FIDELITY: Start like SS-04, end exactly like SS-05; only the presence buttons change state.

CONTINUITY: Grace's watch, polo, mug; same monitor.

AUDIO: Three soft mouse clicks, room tone. No music.

ENDING: Hold on the screen matching SS-05.

NEGATIVE CONSTRAINTS: Do not show "Mark All Present" being used. No overlays, no music.

GENERATION PROMPT: Realistic over-the-shoulder shot, 10 seconds: a woman in a navy polo with a silver wristwatch at a wooden desk clicks "Present" on two guard cards on her monitor, glances at a handwritten call-in sheet on a clipboard, then clicks "Absent" on the third card. The monitor content goes from the supplied screenshot SS-04 to exactly SS-05. Flat, readable screen, locked-off camera, soft daylight, three soft clicks, room tone only, no music, no overlays, ends on a steady frame.
```

**Narration:** "Mark each guard as it really happened: Present, Absent or AWOL."

### DA2-06

```
CLIP ID: DA2-06
COURSE: Daily Attendance: Register, Confirm, Verify
LESSON: How do I register a site's attendance?
SEQUENCE: 6 of 6
DURATION: 10 seconds
PREVIOUS CLIP: DA2-05 (guards marked)
NEXT CLIP: none (end of lesson video)

REFERENCE: Use supplied screenshots SS-05 (start) and SS-07 (end).

SCENE: Grace saves; the guide panel shows Done.

SUBJECT: Monitor screen, then Grace.

ACTION: Clip opens on SS-05 with the pointer moving to "Save Changes" and clicking. The screen becomes SS-07 with the guide panel showing "Done". In the last 3 seconds the camera is still on the screen while Grace's hand lifts off the mouse and reaches for her mug.

CAMERA: Straight-on close-up, locked off.

LIGHTING: Same.

ENVIRONMENT: Monitor bezel, edge of the mug.

UI FIDELITY: SS-05 then SS-07 exactly. The screen change is an instant, ordinary screen update, not an animation.

CONTINUITY: Same monitor, same mug.

AUDIO: One click, room tone. No music, no success chime.

ENDING: Steady hold on SS-07.

NEGATIVE CONSTRAINTS: No confetti, no checkmark animation, no sound effects, no overlays, no fade.

GENERATION PROMPT: Straight-on close-up of a monitor showing the supplied screenshot SS-05; a mouse pointer clicks a "Save Changes" button and the screen instantly updates to the supplied screenshot SS-07, where a narrow panel on the right reads "Done". A woman's hand lifts from the mouse and reaches for a coffee mug at the edge of frame. Flat, readable screen, locked-off camera, soft daylight, one soft click, no music, no celebration effects, 10 seconds, ends on a steady frame.
```

**Narration:** "Then press Save Changes. DeployGuard checks the sheet itself and marks your task done."

---

## 5. Video DA3: "How do I confirm a registered sheet?" (4 clips, ~40 s)

### DA3-01

```
CLIP ID: DA3-01
COURSE: Daily Attendance: Register, Confirm, Verify
LESSON: How do I confirm a registered sheet?
SEQUENCE: 1 of 4
DURATION: 10 seconds
PREVIOUS CLIP: none (opening clip)
NEXT CLIP: DA3-02 (Posting Console, captured)

REFERENCE: Use supplied screenshot SS-08 as the authoritative UI reference.

SCENE: Joseph at his desk sees his Confirm task is ready.

SUBJECT: JOSEPH.

ACTION: Clip opens with Joseph already seated, putting on his reading glasses, reading the "Confirm attendance · ABC Mall" card, then placing his hand on the mouse.

CAMERA: Medium shot from his front-left, monitor on the right third, readable. Locked off.

LIGHTING: Same morning daylight.

ENVIRONMENT: Middle desk of the office from DA1-03.

UI FIDELITY: SS-08 exactly.

CONTINUITY: Joseph's wardrobe and glasses per the bible, matching DA1-03.

AUDIO: Room tone. No music.

ENDING: Steady hold, hand on mouse.

NEGATIVE CONSTRAINTS: No overlays, no music, no camera moves.

GENERATION PROMPT: Realistic medium shot, 10 seconds, locked-off: a Zambian man in his late 20s in a light-blue long-sleeve shirt and dark tie puts on reading glasses at a wooden office desk and reads his monitor, which shows the supplied screenshot SS-08 exactly (a task card "Confirm attendance · ABC Mall"), then rests his hand on the mouse. Small bright Lusaka office, whiteboard behind, soft daylight from the left, quiet room tone, no music, no overlays, ends on a steady frame.
```

**Narration:** "Joseph's confirm task waits until Grace has registered. Then it's ready for him."

### DA3-02

```
CLIP ID: DA3-02
COURSE: Daily Attendance: Register, Confirm, Verify
LESSON: How do I confirm a registered sheet?
SEQUENCE: 2 of 4
DURATION: 10 seconds
PREVIOUS CLIP: DA3-01 (Joseph ready)
NEXT CLIP: DA3-03 (Review & Validate)

REFERENCE: Use supplied screenshot SS-09 as the authoritative UI reference.

SCENE: Joseph checks the marks against his call-in notes.

SUBJECT: JOSEPH and his monitor.

ACTION: Clip opens over his shoulder: his eyes move between a notebook of call-ins and the guard cards on screen; he runs a finger down the notebook, then nods.

CAMERA: Over-the-shoulder from his right, monitor readable, locked off.

LIGHTING: Same.

ENVIRONMENT: A small spiral notebook with handwritten call-in notes.

UI FIDELITY: SS-09 exactly, with the "Captured" status badge visible.

CONTINUITY: Same glasses, shirt, tie.

AUDIO: Room tone, page rustle. No music.

ENDING: Steady hold after the nod.

NEGATIVE CONSTRAINTS: No overlays, no invented data.

GENERATION PROMPT: Realistic over-the-shoulder shot, 10 seconds: a young man in a light-blue shirt, dark tie and reading glasses compares handwritten notes in a spiral notebook with guard cards on his monitor, running a finger down the notebook, then nods. The monitor shows the supplied screenshot SS-09 exactly, including a status badge "Captured". Soft office daylight, locked-off camera, quiet room tone and a page rustle, no music, no overlays, ends steady.
```

**Narration:** "He opens the same sheet and checks each mark against call-ins and leave."

### DA3-03

```
CLIP ID: DA3-03
COURSE: Daily Attendance: Register, Confirm, Verify
LESSON: How do I confirm a registered sheet?
SEQUENCE: 3 of 4
DURATION: 10 seconds
PREVIOUS CLIP: DA3-02 (Joseph nods)
NEXT CLIP: DA3-04 (Ruth verifies)

REFERENCE: Use supplied screenshot SS-09 as the authoritative UI reference.

SCENE: Close-up: Joseph presses Review & Validate.

SUBJECT: Monitor screen and pointer.

ACTION: Clip opens on SS-09; the pointer moves to the highlighted "Review & Validate" button and clicks once.

CAMERA: Straight-on screen close-up, locked off.

LIGHTING: Same.

ENVIRONMENT: Monitor bezel.

UI FIDELITY: SS-09 exactly; the highlight ring as in the screenshot.

CONTINUITY: Same monitor as DA3-02.

AUDIO: One soft click. No music.

ENDING: Steady hold just after the click.

NEGATIVE CONSTRAINTS: No animations, no sound effects, no overlays.

GENERATION PROMPT: Straight-on close-up of a monitor showing the supplied screenshot SS-09 exactly; a mouse pointer moves to a highlighted button "Review & Validate" and clicks once. Flat, sharp, readable screen, locked-off camera, soft daylight, one soft click, no music, no overlays, 10 seconds, ends steady.
```

**Narration:** "If it's right, he presses Review and Validate. He can't confirm a sheet he registered himself."

### DA3-04

```
CLIP ID: DA3-04
COURSE: Daily Attendance: Register, Confirm, Verify
LESSON: How do I confirm a registered sheet?
SEQUENCE: 4 of 4
DURATION: 10 seconds
PREVIOUS CLIP: DA3-03 (Review & Validate clicked)
NEXT CLIP: none (end of lesson video)

REFERENCE: Use supplied screenshot SS-10 as the authoritative UI reference.

SCENE: Ruth verifies and locks the sheet.

SUBJECT: RUTH.

ACTION: Clip opens with Ruth reading the Posting Sheets form; she checks a leave register folder open beside her, then clicks "Verify & lock" and sits back slightly.

CAMERA: Medium shot from her front-right, monitor readable on the left third, locked off.

LIGHTING: Same.

ENVIRONMENT: Right-hand desk from DA1-03, cardigan on chair back, an open leave-register folder.

UI FIDELITY: SS-10 exactly, with "Verify & lock" highlighted.

CONTINUITY: Ruth's wardrobe per the bible, matching DA1-03.

AUDIO: Room tone, one click. No music.

ENDING: Steady hold as she sits back.

NEGATIVE CONSTRAINTS: No confirmation dialogs not in SS-10, no overlays, no music, no fade out.

GENERATION PROMPT: Realistic medium shot, 10 seconds, locked-off: a Zambian woman in her 40s with shoulder-length hair and a maroon blouse, cardigan on her chair, checks an open leave-register folder beside her keyboard, then clicks a button "Verify & lock" on her monitor and sits back slightly. The monitor shows the supplied screenshot SS-10 exactly. Small bright Lusaka office, soft daylight, quiet room tone, one soft click, no music, no overlays, ends on a steady frame with no fade.
```

**Narration:** "Ruth checks it against leave records, and locks it for payroll."

---

## 6. Still images

### IMG-DA-01: course cover (1600 × 900)

```
ASSET ID: IMG-DA-01
PURPOSE: Course cover in My Training
COURSE: Daily Attendance: Register, Confirm, Verify
LESSON: (course-level)
SCENE: Grace at her desk, three-quarter view, looking at her monitor showing SS-01 (small, readable), morning light.
VISUAL REQUIREMENTS: Photorealistic; calm and competent, not staged; clear negative space on the right third for the course title, which is added by the app, not baked in.
CHARACTERS: GRACE (continuity bible).
ENVIRONMENT: The office from the continuity bible.
CAMERA: 35 mm, eye level, shallow depth of field on the background.
LIGHTING: Morning daylight from the left.
TYPOGRAPHY: None in the image.
ON-SCREEN TEXT: Only what SS-01 shows on the monitor.
CONTINUITY: Wardrobe, watch, mug per the bible.
NEGATIVE CONSTRAINTS: No text, no logos besides the small shirt logo, no holograms, no stock-photo smiles, no uniforms other than the polo.
GENERATION PROMPT: Photorealistic 16:9 image of a Zambian woman in her early 30s with short neat braids tied back, navy polo with a small white "DogForce" text logo, silver wristwatch, seated at a wooden desk in a small white-walled Lusaka security-company office, looking calmly at a monitor showing the supplied screenshot SS-01. Coffee mug beside the keyboard, whiteboard with handwritten site names softly blurred, window with half-open blinds casting soft morning light from the left. Empty, uncluttered space on the right third. Natural colours, no text.
```

### IMG-DA-02: Present / Absent / AWOL card (1200 × 800), used in lesson 3

```
ASSET ID: IMG-DA-02
PURPOSE: Explain the three marks at a glance
COURSE: Daily Attendance: Register, Confirm, Verify
LESSON: Present, Absent or AWOL: which one?
SCENE: Three simple, equal panels side by side. 1) A guard at a site gate in the DogForce uniform, standing at post. 2) A phone showing a message "Sick, can't come today" (plain, no brand). 3) An empty gate post with nobody there.
VISUAL REQUIREMENTS: Flat, clean editorial illustration; the DogForce palette of deep navy (as in the supplied DeployGuard screenshot), white and one muted accent; generous spacing.
CHARACTERS: A guard in a plain dark security uniform; no identifiable real person.
ENVIRONMENT: A generic site gate with a boom barrier.
CAMERA: Straight-on panels.
LIGHTING: Even, daylight.
TYPOGRAPHY: Labels under each panel: "Present", "Absent", "AWOL", in a plain sans-serif matching the supplied screenshot's font.
ON-SCREEN TEXT: Exactly those three labels plus the phone message.
CONTINUITY: Colours matching the DeployGuard screenshots.
NEGATIVE CONSTRAINTS: No cartoon exaggeration, no weapons, no emojis, no extra text.
GENERATION PROMPT: Clean flat editorial illustration, three equal side-by-side panels on white, deep navy and one muted accent colour. Panel one: a security guard in a plain dark uniform standing at a gate with a boom barrier, labelled "Present". Panel two: a plain smartphone showing a short message "Sick, can't come today", labelled "Absent". Panel three: the same gate with nobody at the post, labelled "AWOL". Plain sans-serif labels, generous spacing, no other text, no weapons, calm and clear.
```

### IMG-DA-03: the pipeline (1600 × 500), used in lesson 1

```
ASSET ID: IMG-DA-03
PURPOSE: Show Register → Confirm → Verify → Payroll as one handover chain
COURSE: Daily Attendance: Register, Confirm, Verify
LESSON: Why does today's attendance have to be done today?
SCENE: Four rounded steps left to right joined by simple arrows: "Register · Operations Supervisor", "Confirm · Admin", "Verify · HR", "Payroll".
VISUAL REQUIREMENTS: Flat diagram in the DeployGuard palette (deep navy, white, one accent), matching the supplied screenshot style.
CHARACTERS: None, or one small simple person icon per step.
ENVIRONMENT: Plain white background.
CAMERA: Flat.
LIGHTING: n/a.
TYPOGRAPHY: Plain sans-serif matching the screenshots.
ON-SCREEN TEXT: Exactly the four step labels.
CONTINUITY: Same palette as IMG-DA-02.
NEGATIVE CONSTRAINTS: No 3D, no gradients, no glow, no icons beyond simple outlines, no extra words.
GENERATION PROMPT: Minimal flat horizontal process diagram on white: four rounded rectangles in deep navy outline joined by thin arrows, left to right, labelled "Register · Operations Supervisor", "Confirm · Admin", "Verify · HR", "Payroll", each with a small outline person icon except "Payroll". Plain sans-serif text, one muted accent on the arrows, no gradients, no 3D, no extra text.
```
