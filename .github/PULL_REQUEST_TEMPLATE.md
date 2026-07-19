## Summary

<!-- 1-3 bullet points. What changed and why. -->

## Type of change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New tool (additive — new `@mcp.tool` in `server.py`)
- [ ] New scaffold template (additive — new entry in `ScaffoldTemplate` enum)
- [ ] Documentation / CI / repo meta change (no production code touched)
- [ ] Refactor (no behavior change)
- [ ] Breaking change (existing e2e string contracts may shift — call this out!)

## How was it tested?

<!-- Paste the e2e / pytest output, or describe the manual GUI run. -->

## Checklist

- [ ] I added at least one new test (`e2e_new_tools_vN.py`) — or explained why not
- [ ] The new test passes locally (`python e2e_new_tools_vN.py`)
- [ ] I did NOT change any string output that an existing e2e test asserts on (or I did and called it out above)
- [ ] `server.py` is still ≤ 4800 lines (currently around 4700)
- [ ] I updated `CHANGELOG.md` if this is user-visible
- [ ] I updated `README.md` tool table if I added/removed a tool

## Related issues

<!-- Link to the issue this closes. Use `Closes #42` syntax. -->