# Damir Job Hunter V9

Every 6 hours GitHub searches UN job feeds for construction, infrastructure, WASH,
contracts, facilities and architecture jobs. No AI, no passwords, no cost.

## Where you see the jobs

| Where | What you do |
|---|---|
| **Email** | Nothing. When new jobs appear, they are posted to the issue **Jobs for Damir** and GitHub emails it to you. |
| **Web page** | Open `https://YOUR-USERNAME.github.io/YOUR-REPOSITORY/` (bookmark it). |
| **Run summary** | **Actions** → click the latest **jobs** run → scroll down. Always works, even without the web page. |

## Setup (once, 10 minutes, all in the browser)

1. **New repository** → any name → **Public** → **Create repository**.
2. Click **uploading an existing file** → drag in `hunter.py` and `README.md` → **Commit changes**.
3. **Add file → Create new file** → type the name `.github/workflows/jobs.yml`
   (the slashes create the folders) → paste the block below → **Commit changes**.
4. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
5. At the top of the repository: **Watch → All Activity** (this sends the emails).
6. **Actions → jobs → Run workflow → Run workflow.** After about 1 minute both boxes,
   **hunt** and **page**, show a green ✓. The first email lists all jobs found now;
   later emails list only new ones.

```yaml
name: jobs
on:
  schedule:
    - cron: "15 */6 * * *"
  workflow_dispatch:
permissions:
  contents: read
  issues: write
  pages: write
  id-token: write
concurrency:
  group: jobs
  cancel-in-progress: false
jobs:
  hunt:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v5
      - run: python hunter.py
        env:
          GITHUB_TOKEN: ${{ github.token }}
      - uses: actions/upload-pages-artifact@v5
        with:
          path: site
  page:
    needs: hunt
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    steps:
      - id: deploy
        uses: actions/deploy-pages@v5
```

## If something is wrong

| You see | Do this |
|---|---|
| **page** is red, **hunt** is green | Step 4 was skipped. Do it, then Run workflow again. Email and summary already work. |
| No email | Step 5, and check github.com → Settings → Notifications → Email is on. The issue still shows the jobs. |
| Feeds show ❌ | That job site is blocking the search. The other sites still work. Send the ❌ line for a fix. |
| Runs stop after 2 months | GitHub pauses schedules after 60 days without commits. Actions → jobs → **Enable workflow**. |

Tier A ≥ 50, B ≥ 35, C ≥ 25 is reading order, not an apply decision. Always check eligibility
and the deadline on the original vacancy. Do not close or delete the issue: it is also the
record of which jobs were already emailed. To tune the search, edit the RULES block in
`hunter.py` and upload it again.
