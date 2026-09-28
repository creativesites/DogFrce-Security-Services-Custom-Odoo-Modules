# Course: Daily Attendance (Register, Confirm, Verify)

> Seeded as data in `custom_addons/security_deployguard_ops/data/training_course.xml`
> (course code `daily-attendance`). Media prompts: [`MEDIA-PROMPTS.md`](./MEDIA-PROMPTS.md).

## Who it's for

Auto-enrolled for the three people in the attendance pipeline
(docs/deployguard/dogforce-roles-and-pipeline.md):

| Role | Group | Their lesson |
|---|---|---|
| Operations Supervisor | `security_base.group_security_supervisor` | Register |
| Admin | `security_operations.group_security_front_desk` | Confirm |
| HR | `security_base.group_security_hr_payroll_officer` | Verify |

Due 7 days after enrolment. A responsibility created by the pipeline setup
wizard links this course as "Learn this first", so each person's Today card
offers it until they complete it. **It never blocks the work.**

## Structure: one operational question per lesson

| # | Lesson | Type | Guided practice | Video ID |
|---|---|---|---|---|
| 1 | Why does today's attendance have to be done today? | video + text | — | DA1 (4 clips, ~40 s) |
| 2 | How do I register a site's attendance? | video + text | — | DA2 (6 clips, ~60 s) |
| 3 | Present, Absent or AWOL: which one? | text | — | image asset IMG-DA-02 |
| 4 | Do it: register today's attendance with DeployGuard beside you | guided | `attendance_register` | — |
| 5 | How do I confirm a registered sheet? | video + guided | `attendance_confirm` | DA3 (4 clips, ~40 s) |
| 6 | How does HR verify and lock a day? | text + guided | `attendance_verify` | — |
| 7 | What if something doesn't match? | text | — | — |
| — | Assessment: 5 questions, 80 % to pass, 3 attempts | | | |

Lessons 4 to 6 are the core of the course. "Practice it now" starts the real
guided task in the ERP, and if the employee has a real task that day, the
guide uses it. **Practising is doing.** This is the "teach me while I actually
perform the task" principle from the V2 brief.

## Producing the videos

1. Take the screenshots listed in `MEDIA-PROMPTS.md` §2 from **staging** (not
   production: no real guard names on screen).
2. Generate each 10-second clip with Gemini, using its prompt and the named
   screenshot as the reference image.
3. Join the clips in order (DA1-01 … DA1-04) with straight cuts and no
   transitions. Clips are designed to cut together (§1 continuity bible).
4. Record the narration lines as one continuous voice-over over the
   joined video. Lines are written to end on clip boundaries.
5. Upload the MP4 somewhere the desktop can play it (an `https://` link to an
   `.mp4`/`.webm` file, or YouTube-nocookie/Vimeo, which the CSP allows) and
   paste the URL over the matching `REPLACE_WITH_HOSTED_VIDEO_URL_DA*` in the
   lesson (Training → Courses → edit a new draft version, then publish).
   Until then the lesson shows the written walkthrough instead.
