# Publication Checklist

[English](publication-checklist.md) | [한국어](ko/publication-checklist.md) | [日本語](ja/publication-checklist.md)

Use this checklist for source files, Git history, backup archives, build photos, audio, and demo videos.

## Secrets and history

- [ ] No `.env`, live API key, password, private key, or service-account file is tracked.
- [ ] All branches, tags, commits, archives, bytecode, logs, and editor backups were scanned.
- [ ] Any exposed credential was revoked before repository cleanup.
- [ ] `.env.example` contains placeholders only.

```bash
git status --ignored
git ls-files
git grep -n -I -E "AIza|API_KEY|secret|token|password|credential"
git log -p --all | rg -i "AIza|API_KEY|secret|token|password|BEGIN .*PRIVATE KEY"
```

Do not paste discovered values into issues or documentation. Revoke first, then assess history, forks, and caches.

## Privacy and media

- [ ] Names, email addresses, phone numbers, local paths, device names, Wi-Fi, IP, SSH, and port-forwarding details were reviewed.
- [ ] Photos and videos do not expose faces, private voices, documents, IDs, labels, or license plates without consent.
- [ ] EXIF and location metadata were reviewed.
- [ ] YouTube visibility and logged-out link access match the intended scope.
- [ ] Captured JPEG and audio files are not unintentionally tracked.
- [ ] Network use by Gemini, Google speech recognition, and gTTS is documented.

## Code and documentation agreement

- [ ] `python main_brain.py` is documented as the current physical entrypoint.
- [ ] `test_case.py` is described as planning-only, not a hardware test.
- [ ] The Gemini JSON plan, allowlisted dispatcher, and `hardware.py` path are described accurately.
- [ ] GPIO, camera, microphone, ultrasonic pins, and thresholds match the code.
- [ ] The 25 cm single-forward guard and 18 cm continuous-motion stop are distinguished.
- [ ] Sensor timeout, missing rear/side sensors, and missing physical emergency stop are listed as limitations.
- [ ] `2main_brain.py` is not presented as runnable current code.
- [ ] Demo capabilities and the restored integrated source are linked to the same implementation lineage.

## Physical safety

- [ ] HC-SR04 ECHO is level-shifted from 5 V to 3.3 V.
- [ ] Motor supply, driver, common ground, and protection are verified.
- [ ] Direction, stop, and distance guards were tested with wheels raised.
- [ ] An accessible physical motor-power switch is available.
- [ ] Initial motion tests use low speed in a clear space.

## Final repository checks

- [ ] Clone links use `cora1022/gemini-raspberry-pi-robot.git`.
- [ ] Relative links and images resolve.
- [ ] Python syntax checks pass.
- [ ] `git diff --check` and secret scans pass.
- [ ] Licenses and external asset permissions are verified.
- [ ] Setup instructions were reviewed from a fresh clone.
