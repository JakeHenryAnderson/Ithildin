# Command Center Pre-UAT Accessibility, Authority, and UI Review

Status: superseded by independent Sol Ultra pre-UAT review; remediation in progress; not ready for
fresh-operator UAT.

Base commit: `6a357bd4bb7e7a7dc10abeb4bfa834addf64175c`
Governed tool count: `24`
Runtime/API/authority change at initial review: none

This document records the initial focused review. A later independent Sol Ultra review found four
high-severity blockers and six medium findings, so this document no longer closes the step between
`CC-PILOT-106` and `CC-PILOT-107`. See the
[independent findings register](command-center-sol-ultra-pre-uat-review.md). Neither review is a
WCAG conformance claim, accessibility certification, product acceptance, release evidence, or
substitute for fresh-operator UAT.

## Review Scope

- keyboard entry and visible focus treatment;
- skip-to-content behavior;
- focus transfer after Attention, specialist navigation, and approval cross-links;
- hidden lens target behavior;
- reduced-motion preference;
- control labels, disabled states, heading/region structure, tables, status text, and non-color state;
- intermediate desktop overflow and responsive collapse rules;
- authority, lifecycle, evidence, signing, export, and presentation-lens wording;
- live local-preview behavior and browser console state.

## Findings and Disposition

| Finding | Severity | Result | Evidence |
| --- | --- | --- | --- |
| `A11Y-001` most controls lacked an explicit high-visibility keyboard focus indicator | medium | fixed | global `:focus-visible` treatment for buttons, links, form fields, textareas, and summaries |
| `A11Y-002` Attention/source navigation scrolled without moving keyboard focus | medium | fixed | focusable target regions plus `scrollAndFocusElement` and focused UI assertions |
| `A11Y-003` Evidence/Administration links could target specialist sections absent from the current lens | medium | fixed | lens-aware navigation renders the target before scrolling/focusing |
| `A11Y-004` programmatic smooth scrolling ignored reduced-motion preference | low | fixed | `prefers-reduced-motion` selects automatic scrolling and disables skip-link transition |
| `A11Y-005` no keyboard bypass for repeated header/navigation controls | medium | fixed | first-focus skip link transfers focus to operator Attention |
| `A11Y-006` disabled action state relied on native styling alone | low | fixed | visible opacity plus non-action cursor while native `disabled` remains authoritative |
| `UI-001` run and investigator controls were over-dense at intermediate desktop widths | medium | fixed | server controls use a bounded four-column grid; investigator controls use three columns; both collapse at the existing responsive breakpoint |
| `UI-002` status values containing spaces produced unstable CSS class tokens | low | fixed | status class token normalizes whitespace while visible status text remains unchanged |
| `AUTH-001` specialist lenses could be mistaken for authorization roles | high if present | cleared | persistent wording states presentation only and no role, permission, or Gateway authority; implementation uses local UI state only |
| `AUTH-002` lifecycle/evidence labels could overclaim completion, signing, custody, or external coverage | high if present | cleared | applied/reviewed/promoted/released, local verification, signing reference, download, custody, and off-platform limitations remain separate and explicit |

## Focused Test and Live Evidence

The UI interaction harness verifies:

- skip link is the first keyboard stop and transfers focus to Attention;
- specialist navigation renders and focuses its target;
- opening an Attention item focuses the Workbench target;
- Routine, Investigation, Policy Administration, and Technical Review retain distinct inventories;
- all prior decision, artifact, evidence, export, and filter behavior remains covered.

Live browser QA confirmed:

- Administration navigation activated Policy Administration and focused `#administration`;
- the focused specialist region had a visible outline;
- the 1280-pixel live viewport had equal document/client widths and no horizontal overflow;
- status text remained visible in addition to color;
- browser logs contained no warnings or errors beyond normal Vite/React development messages.

The responsive rules were code-reviewed for one-column collapse at 980 pixels and artifact
list/detail collapse at 1120 pixels. A separate live narrow-viewport and screen-reader session was
not performed and is not claimed.

## Historical Validation

The following commands were reported after the initial review fixes. They are historical evidence,
not validation of the remediated integrated candidate. The `review_docs.py` invocation was a no-op
and is intentionally excluded from the future authoritative command set.

```text
make ui-test
make typecheck
make tool-surface-invariant-gate
make no-new-powers-guardrail
make agent-workflow-check
uv run pytest tests/test_release_readiness.py tests/test_docs_site.py -q
make lint
make docs-site
git diff --check
```

## Initial Authority Review Result (Superseded)

- Command Center remains a presentation and existing-API client.
- Gateway remains enforcement, policy, approval, execution, and audit authority.
- Presentation lenses are not roles or access controls.
- No registered-tool, applied-artifact, verified-chain, signing, export, or evidence label implies a
  broader permission, review, promotion, custody, release, compliance, or enterprise claim.
- Tool count remains `24`; no governed power was added.

## Residual Human Work

Before `CC-PILOT-107`, close the independent findings, bind the candidate to a reproducible commit,
pass the authoritative gates, and obtain an independent closure review. UAT must then test uncoached
comprehension and wrong-path recovery with a fresh operator. Include representative keyboard-only,
high-zoom, narrow-viewport, and screen-reader evidence where those users are in pilot scope. No
formal accessibility conformance claim is authorized from either internal review.
