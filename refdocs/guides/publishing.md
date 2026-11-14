# Publishing

> **v4 is frozen (D-84, 2026-11-14).** The closeout commit was pushed once to both remotes below. Nothing more is pushed from v4 except a security or secrets fix.

| Branch | Remote | Repository | Visibility | Holds |
|---|---|---|---|---|
| `main` | `origin` | Synapse-v4 | Private | Product development, no event context |
| `codefest` | `hackathon` | DANG-WANGI-Education-and-Human-Development | Public | `main` plus `CODEFEST.md` and a pointer in its README |

Every update:

```
git switch main
# work, commit
git push origin main

git switch codefest
git merge main
git push hackathon codefest:main
git switch main
```

Never merge `codefest` into `main`.

Because the mirror is public, check before pushing that nothing new is a secret, personal data, a textbook passage, event admin or business material (CLAUDE.md hard constraint 13). `founder/` and `refdocs/business/` are ignored for this reason.

`.git/hooks/pre-push` refuses any other branch on the `hackathon` remote and any tip holding those two folders. Hooks are not cloned: on a new machine, install it again.
