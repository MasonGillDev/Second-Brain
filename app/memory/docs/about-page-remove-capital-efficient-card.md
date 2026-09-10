# Remove "Capital Efficient" Card from Production /about Page

**Project:** SLYD Website
**Date:** 2026-07-22
**Author:** f3a6495e-7540-43cb-beb4-0285e8c4713d
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done
Mason spotted a "Capital Efficient" card on the live slyd.com /about page claiming "SLYD was built for under $500K while competitors raised $55M+ before generating revenue" and wanted it removed from production without shipping any of the in-progress development-branch work.

Key findings:
- The card lived only on the `main` branch in `Components/Pages/About.razor` (lines 231–235), inside the `about-differentiator-grid` (4 cards: Sovereign AI First, Partners Not Vendors, Capital Efficient, Vertically Integrated).
- The `development` branch's rewritten About page does NOT contain this card, so no backport is needed — when development is promoted, its About page replaces main's entirely.
- A related "over-speccing" line also exists in `HardwareSales.razor` on main; Mason chose to leave that alone.

Approach: created an isolated git worktree at `../website-hotfix` on a new branch `hotfix/remove-capital-efficient-card` cut from `origin/main` (HEAD d63a736). This left the local `development` checkout and its uncommitted `Configure.razor` changes completely untouched. Removed the 6-line card block, verified `dotnet build` passes (0 errors), committed as `fd120dd`, and pushed the branch to origin. The differentiator grid is 2-column, so the remaining 3 cards render 2-over-1 — accepted as-is.

Note: the first `git push` and `git ls-remote` hung (credential prompt); retrying with `GIT_TERMINAL_PROMPT=0` pushed cleanly. Worktree was removed after the push.

## To Do Next
- Mason will open the PR on GitHub: https://github.com/SLYD-Platform/website/pull/new/hotfix/remove-capital-efficient-card (merge into `main`; merging triggers the prod deploy).
- After merge, verify the card is gone on https://slyd.com/about.
- Local branch `hotfix/remove-capital-efficient-card` can be deleted after the PR merges.
