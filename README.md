# Deal Ladder: live UK deal roles for an ACA moving out of audit

Finds live UK roles in transaction services (financial due diligence), corporate finance / M&A,
investment banking, private equity and PE portfolio / fund finance, then ranks them for the
profile in the `PROFILE_JSON` repository secret (an example is in `profile.example.json`) by
pay, how reachable each role is, fit with those areas and a London preference.

The deciding rule: adverts that **require** previous deal experience (TS, due diligence, M&A,
corporate finance, IB or PE) are marked and hidden on the page by default. "Desirable", "a plus"
and "audit or TS experience" stay in, and adverts that welcome people moving from audit are
marked as open to audit backgrounds.

## Sources

| Source | Employers |
|---|---|
| eFinancialCareers (public keyword and job pages, one request every 10 s as its robots.txt asks) | The wider UK market: Big 4 and mid-tier deal teams, A&M, Kroll, boutiques, PE firms and recruiter ads |
| Own careers sites | KPMG UK, Deloitte UK, EY, BDO UK, Goldman Sachs, Rothschild & Co |
| Greenhouse / SmartRecruiters / Workable / Oleeo / Eightfold / Oracle | General Atlantic, Lincoln International, William Blair, Teneo, FRP Advisory, Evelyn Partners, Interpath, Evercore, Jefferies, HSBC, J.P. Morgan, Lazard |
| Workday | Morgan Stanley, Citi, Barclays, Deutsche Bank, Bank of America, MUFG, Mizuho, Lloyds, Blackstone, Carlyle, Apollo, Houlihan Lokey, ICG, PwC, Grant Thornton UK, RSM UK (Workday has been refusing GitHub's servers since Nov 2026; a site that fails keeps its last roles for 7 days) |
| Optional free keys | Reed (`REED_API_KEY`), Adzuna (`ADZUNA_APP_ID` + `ADZUNA_APP_KEY`) as repository secrets |

## Run locally

    python3 -m finder.run          # writes data/jobs.json and data/report.md
    python3 -m http.server         # then open http://localhost:8000

The GitHub Actions workflow runs it every morning and commits `data/`; GitHub Pages serves the page.
