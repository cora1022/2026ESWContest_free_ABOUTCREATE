# Publication Checklist

Use this checklist before changing the repository visibility to public.

## Required Before Public

- Verify no secret-like values remain in current files.
- Verify no secret-like values remain in `git log --all`.
- Confirm `.env` and `.env.*` are ignored, while `.env.example` stays tracked.
- Confirm no real microphone recordings, private images, or personal data are committed.

## Commands

Current-file check:

Use a secret scanner or search for provider-specific key prefixes before publishing.

History check:

```bash
git log --all --name-only --pretty=format: | rg -i "\.env|pem|key|secret|token|credential|service.?account"
```

## Current Status

Before publishing, run the checks above and keep real keys outside Git.
