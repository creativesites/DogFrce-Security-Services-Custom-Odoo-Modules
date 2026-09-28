# Releasing DeployGuard Desktop (Windows)

Release criterion: **a DogForce employee can install it on Windows and do their
work reliably.** "It works on my Mac" is not a release.

There are three separate kinds of signing. Don't confuse them.

| | What it proves | Where the key lives | Without it |
|---|---|---|---|
| **Updater signing** (minisign) | An update really came from us | `TAURI_SIGNING_PRIVATE_KEY` (+ `_PASSWORD`) CI secret; backup off the laptop | Releases are refused by CI; installed apps reject the update |
| **Windows code signing** (Authenticode) | The installer's publisher is DogForce | `WINDOWS_CERTIFICATE` (base64 PFX) + `WINDOWS_CERTIFICATE_PASSWORD` CI secrets | Installer works, but SmartScreen shows "Windows protected your PC". **Do not claim SmartScreen trust until a real certificate exists.** |
| **Release publishing** | The updater can find the new version | `RELEASES_TOKEN` (fine-grained PAT with contents:write on `creativesites/dogforce-desktop-releases`) | Nothing is published |

## One-time setup (owner: Winston)

1. Back up `~/.tauri/dogforce-updater.key` and its password to the password
   vault. **If this key is lost, installed apps can never auto-update again.**
2. Add repository secrets `TAURI_SIGNING_PRIVATE_KEY` (the key file's contents)
   and `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`.
3. Create the public repo `creativesites/dogforce-desktop-releases` (the
   updater endpoint in `src-tauri/tauri.conf.json` reads
   `releases/latest/download/latest.json` from it) and add `RELEASES_TOKEN`.
4. Optional: buy an OV/EV code-signing certificate (or Azure Trusted Signing)
   and add `WINDOWS_CERTIFICATE`/`WINDOWS_CERTIFICATE_PASSWORD`.

## Cutting a release

1. Bump the version in **all three** of `package.json`, `src-tauri/tauri.conf.json`
   and `src-tauri/Cargo.toml`. CI fails if they differ.
2. Merge to `main`; wait for the `checks` job to be green.
3. Tag and push: `git tag desktop-v0.3.0 && git push origin desktop-v0.3.0`.
4. The `release` job builds the updater-signed NSIS installer (Authenticode-signed
   too if the certificate secret exists) and publishes the installer and
   `latest.json` to the releases repo as `v0.3.0`.
5. Installed apps see it on their next launch or within 6 hours. **They never
   restart on their own.** The employee chooses "Update now" when convenient.

A manual fallback from macOS still exists: `scripts/build-windows-xcompile.sh`
(needs `brew install llvm nsis` and the key in `~/.tauri`).

## First install on an employee PC

1. Download `DogForce-Security-Services_<version>_x64-setup.exe` from the
   releases repo.
2. Run it. It installs per-user; no administrator rights are needed.
   Without code signing, choose **More info → Run anyway** on the SmartScreen
   prompt. Tell the employee to expect this.
3. WebView2 is installed automatically if the PC lacks it (Windows 11 has it).
4. Sign in with the employee's normal DogForce ERP login.

## Manual QA before handing out a release

Run on a clean Windows 10 or 11 VM against **staging** first, then against
production with a real employee account. Tick every box.

### Install and update
- [ ] Fresh install, launch, and the window opens at a sensible size
- [ ] Install version N, publish N+1: the update notice appears; nothing restarts until "Update now"; after the update the version is N+1 and you are still signed in

### Authentication
- [ ] First launch shows DogForce ERP's own login page
- [ ] Signing in opens DeployGuard automatically, once
- [ ] Browsing Odoo pages afterwards does **not** re-open DeployGuard or onboarding
- [ ] Sign out returns to the login page, and DeployGuard shows "Sign in to continue"
- [ ] Session expiry: delete the session on the server (or wait it out), then use any DeployGuard screen. You see "Your session expired / Sign in again", not a blank or broken screen

### Connectivity (honest states)
- [ ] Wi-Fi off: the toolbar shows "You're offline"
- [ ] Network on but Odoo stopped: "DogForce ERP is unavailable"
- [ ] Nothing claims success while offline (try submitting a task: you see an error, and the task is not marked done)

### Navigation and window
- [ ] Back / Forward / Reload act on Odoo; Reload refreshes the DeployGuard page while it is open
- [ ] DogForce button toggles the app view; Escape returns to Odoo
- [ ] Ctrl+K opens quick actions; Help and Report open full-size, not clipped
- [ ] Resize, maximise, restore, minimise; drag the window by the toolbar
- [ ] Keyboard only: Tab reaches every control; focus is visible; dialogs trap focus and Escape returns it

### Work
- [ ] Today lists today's tasks with what, why and due time
- [ ] Task detail → Start → checklist answers save → Submit
- [ ] "Couldn't complete" requires a reason and shows on Team Today
- [ ] Clearing a number answer works

### Guided task (V2 slice: attendance)
- [ ] Ops Supervisor: Today shows "Register attendance: <site>" for each rostered site
- [ ] "Learn this first" appears if the course isn't done; the lesson's "Practice it now" starts guidance
- [ ] "Guide me": Odoo shrinks left, the guide panel appears right; the real Odoo control is highlighted
- [ ] Wander to another menu: the panel says where you are and how to get back
- [ ] "Show me" pulses the target; "I'm stuck" shows help, then the AI explanation (labelled as AI)
- [ ] Capture the batch: the step completes, the task becomes Submitted, and the panel says Done
- [ ] Admin's "Confirm attendance" task shows "waiting for Register" until capture, then becomes ready
- [ ] GM (Team Today): sees who registered, who confirmed, and what is stuck; each number opens the real records
- [ ] Leave a task past due: the overdue sweep raises an Exception with the task as evidence

### Training
- [ ] Course list → lesson → video plays (if set) → Mark complete
- [ ] Opening the assessment doesn't use an attempt until Start
- [ ] "Try it in DogForce ERP" opens the right Odoo screen

### Production compatibility
- [ ] Against a server **without** optional modules (security_guidance, security_support, security_adoption), screens disappear rather than erroring; no "[object Object]"; the rest works

### First run
- [ ] New user: welcome → monitoring notice (must be acknowledged) → ready
- [ ] Relaunch: no onboarding again. Same user on another PC: notice not asked again (it is recorded on the server)

### Security spot-checks
- [ ] In the Odoo webview, a link to an external site opens the system browser, not inside the app
- [ ] DevTools on the shell (debug build only): `localStorage` has no `session_id` or password
- [ ] Problem-report "See exactly what is sent" shows no cookie or password
- [ ] Log file (`%LOCALAPPDATA%\com.deployguard.desktop\logs`) has no passwords, cookies or tracebacks
