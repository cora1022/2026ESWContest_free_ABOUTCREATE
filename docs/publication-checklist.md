# Publication Checklist

Use this checklist before changing the repository visibility to public.

## Required Before Public

- Revoke and regenerate the exposed Google API key.
- Remove secret-containing commits from the default branch history.
- Verify no secret-like values remain in current files.
- Verify no secret-like values remain in `git log --all`.
- Confirm `.env` and `.env.*` are ignored, while `.env.example` stays tracked.
- Confirm no real microphone recordings, private images, or personal data are committed.

## Commands

Current-file check:

```bash
rg -n --pcre2 "\bAIza[0-9A-Za-z_-]{30,}\b|\bsk-[A-Za-z0-9_-]{30,}\b|\bgh[pousr]_[A-Za-z0-9_]{30,}\b|-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----|\b(?:AKIA|ASIA)[0-9A-Z]{16}\b" .
```

History check:

```bash
git log --all -S "AIza" --oneline --decorate
git log --all --name-only --pretty=format: | rg -i "\.env|pem|key|secret|token|credential|service.?account"
```

## Current Status

Public release is blocked until the exposed key is revoked and the default branch history is cleaned. The documentation branch removes the key from current files, but the repository should remain private until the checklist above passes.
