# AI Health Compliance Tracker

Tracks whether New York hospitals' financial assistance materials comply with state law, graded against the CSSNY 17-criterion Hospital Financial Assistance (HFAL) rubric. A scheduled Claude agent re-checks hospitals' posted policies, applications and summaries, and commits every change here, so the git history is the audit trail.

**Data health dashboard:** https://seyounglee2001.github.io/AI-health-compliance-tracker/ (what's missing, what needs a human, how fresh the data is)

**Open the spreadsheet:** [`audit/exports/hfal-compliance-tracker.xlsx`](audit/exports/hfal-compliance-tracker.xlsx)

| | |
|---|---|
| Hospitals | 212, in 71 health systems |
| Baseline | Full re-audit on November 9, 2026, compared against the September 2025 grades |
| Updates | The agent runs weekdays and re-checks the 10 health systems checked longest ago (all 71 about every 1.5 weeks) |
| Data | [`audit/tracker.csv`](audit/tracker.csv), one row per hospital, with **Last Updated** and **Last Checked** dates |
| History | [`audit/changelog.csv`](audit/changelog.csv) lists every field change (old → new), and every run is one commit |

Refer to the following for documentation on the agent: [`audit/README.md`](audit/README.md).
