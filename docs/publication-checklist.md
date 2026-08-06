# Publication Checklist

[English](publication-checklist.md) | [한국어](ko/publication-checklist.md)

Use this checklist before publishing source, images, recordings, or demo links.

## Secrets and Git History

- Confirm `.env` and real API keys are not tracked.
- Search current files and every reachable Git commit for keys, tokens, credentials, private keys, Wi-Fi passwords, and service-account files.
- Remember that deleting a secret from the latest commit does not remove it from Git history. Revoke exposed credentials first.

```bash
git status --ignored
git grep -n -I -E "GOOGLE_API_KEY|AIza|secret|token|password|credential"
git log -p --all | rg -i "GOOGLE_API_KEY|AIza|secret|token|password|credential|BEGIN .*PRIVATE KEY"
```

## Personal and Location Data

- Review names, email addresses, usernames, hostnames, IP addresses, home paths, device serial numbers, and command history.
- Remove Wi-Fi SSIDs, passwords, access points, static network details, and precise physical locations.
- Check image metadata and visible backgrounds, screens, labels, reflections, badges, and documents.
- Review voice recordings for names, conversations, addresses, or other identifying details.

## Demo Scope

- Confirm every person visible or audible has agreed to publication.
- Confirm thumbnails and linked videos have the intended visibility.
- Describe recorded prototype features separately from features reproducible with public code.
- Do not imply that prompt instructions provide a hardware safety guarantee.

## Final Repository Review

- Test all relative documentation and image links.
- Confirm the clone URL and setup commands use the current repository name.
- Verify the license and third-party asset permissions.
- Review the diff and commit list one final time from a clean clone if possible.
