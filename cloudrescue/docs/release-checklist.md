# Release checklist

- Review the source, history, benchmark methodology, screenshot, and security findings.
- Keep MIT for CloudRescue and the trace utility. Verify redistributed notices and resolve or formally accept open dependency advisories before public release.
- Review the repository privately first. Create an empty private GitHub repository under the approved owner, then add its URL as `origin` and push `feature/external-validation` after approval.
- Open a CloudRescue pull request into the intended default branch. Require the GitHub Actions verification job, inspect the disposable PostgreSQL logs, and verify that no generated reports or secrets were uploaded.
- After review, merge, choose a version, prepare release notes and provenance, and obtain explicit approval before changing repository visibility or tagging a public release.
- Keep Azure SDK and PyPI submissions separate. The first proposed PR is a CloudRescue review of the trace validator and loopback experiment, with its evidence and limitations. An Azure SDK PR would need a distinct verified gap.

After approving a private repository and committing the reviewed Phase 5 changes, run from PowerShell:

```powershell
git remote add origin <approved-private-repository-url>
git push -u origin feature/external-validation
```

If the new repository is empty, establish its default branch from the reviewed Phase 4 baseline before opening the Phase 5 comparison. Keep generated raw evidence local or distribute a reviewed, sanitized copy separately.
