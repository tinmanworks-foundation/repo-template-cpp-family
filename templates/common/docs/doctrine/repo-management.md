# Repo Governance Doctrine

Status: Stable  
Last Reviewed: 2026-02-28

## Scope

Applies to all repositories in this ecosystem.
This is policy and doctrine, not automation.

## Companion Artifacts

- Governance process: [`doctrine-governance.md`](doctrine-governance.md)
- Repo visibility note template: [`templates/repo-visibility-note-template.md`](templates/repo-visibility-note-template.md)
- Doctrine change record template: [`templates/doctrine-change-record-template.md`](templates/doctrine-change-record-template.md)

## Rule Order (enforce in this order)

1. Commit signing policy
2. Repo placement policy (Personal vs Organization)
3. Visibility policy (Public vs Private vs Internal)

## Commit Signing Policy

### Required outcome

- All local commits are signed.
- Protected branches reject unsigned commits.

### Local baseline

Preferred method: SSH commit signing.

Required git settings:

```bash
git config --global gpg.format ssh
git config --global user.signingkey "~/.ssh/id_ed25519.pub"
git config --global commit.gpgsign true
git config --global tag.gpgsign true
```

Verification:

```bash
git log --show-signature -1
git tag -v vX.Y
```

Expected result:

- Local signature is present.
- GitHub shows `Verified` on commits.
- Release tags are signed and verified.

Tag signing rule:

- Release tags must be signed (`git tag -s`), not only annotated (`git tag -a`).
- Ensure the SSH public key is added on GitHub as a Signing Key so verification appears.

### GitHub enforcement baseline

For important repositories (templates, core libs, product repos), enable:

- Require signed commits
- Require pull request
- Require status checks to pass
- Restrict who can push (optional)
- Require linear history (optional)

If using an organization, prefer organization rulesets over per-repo configuration.

## Repo Placement Policy (Personal vs Organization)

### Keep in personal account when

- Repo is a personal experiment or short-lived one-off.
- Repo is expected to be deleted or rewritten frequently.
- Repo is truly solo and not part of a shared ecosystem.

### Place in organization when

- Repo is part of a multi-repo ecosystem.
- Repo is depended on by other repos.
- Policy enforcement is required at scale.
- Collaboration is likely now or later.
- Project branding should be separated from personal identity.

### Practical placement rule

If a repo is meant to be depended on by other repos, or requires governance at scale, it belongs in the organization.

## Visibility Policy (Public vs Private vs Internal)

### Decision tree

Public by default only if all are true:

- Comfortable with strangers reading it.
- No secrets, private endpoints, credentials, or proprietary material.
- README and license are ready enough for outside readers.

Private if any are true:

- Contains credentials, tokens, personal data, private links, invoices, or internal notes.
- Contains unfinished work not ready for indexing.
- Contains university/company code, NDA content, or anything that could be interpreted as work product.

Internal only when:

- Using a GitHub Organization that supports internal repos.
- Access should be limited to organization members.

### Mandatory repo annotation

Every repository must include a visibility note in `README.md` or `POLICY.md`:

- `Visibility: Public | Private | Internal`
- `Reason: ...`
- `Promotion criteria to Public: ...`

### Safe-to-make-public gate

Before changing visibility to public, confirm:

- No secrets (`.env`, API keys, tokens, private keys, passwords, Wi-Fi configs).
- `.gitignore` is correct.
- License is present.
- README has purpose and build/run basics.
- Large binaries or private assets are removed.
- Personal notes are moved to a private docs repository if needed.

No exceptions for "temporary public." Public implies durable exposure.

## Repository Workflow (Doctrine repo only)

This section applies only to this Doctrine repository.

### Branch model

- `master` -> stable snapshots (may include Draft files)
- `develop` -> working branch
- `feature/*` -> short-lived heavy refactor branches

### Release process

1. Create `release/vX.Y` from `develop`.
2. On release branch:
   - Promote ready files `Draft -> Stable`.
   - Leave others `Draft`.
   - Update [`RELEASE_NOTES.md`](RELEASE_NOTES.md).
3. Merge release to `master`.
4. Create signed tag on `master`:
   - `git tag -s vX.Y -m "Release vX.Y"`
5. Push `master` and tag:
   - `git push origin master`
   - `git push origin vX.Y`
6. If tag was created unsigned by mistake, recreate it as signed on the same commit and force-push:
   - `git tag -d vX.Y`
   - `git tag -s vX.Y -m "Release vX.Y" <release-commit>`
   - `git push --force origin vX.Y`

### Document status model

Each file must contain:

- `Status: Draft | Stable | Deprecated`
- `Last Reviewed` date

Definitions:

- `Draft`: May change.
- `Stable`: Safe for AI copy/paste.
- `Deprecated`: Kept for reference; avoid new dependency.

### Tag meaning

Tags mark stable repository snapshots.
They do not imply all files are `Stable`.
