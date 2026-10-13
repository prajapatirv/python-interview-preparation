---
id: production
title: Production incidents & troubleshooting
order: 9
summary: Outages, incident response, RCA and how you led it (performance tuning has its own topic).
crib: java/java-interview-prep/topics/16-production-troubleshooting-rca.md
docs: java/java-interview-prep/deep_dive/18_production_troubleshooting.md, java/java-interview-prep/deep_dive/23_production_scenarios.md
examples: java/java-interview-prep/examples/23_production_scenarios
keywords: production, incident, outage, troubleshoot, troubleshooting, rca, root cause, rollback, hotfix, on-call, postmortem, war room, sev1, downtime
---
Skill focus for Production incidents & troubleshooting answers:
- Use the arc: detect -> mitigate first (rollback, scale, feature flag) -> diagnose with evidence (thread dumps, heap dumps, GC logs, Splunk, APM) -> fix -> blameless RCA -> prevention.
- Name concrete tools: jstack/jcmd, heap histograms, GC logs, Actuator, Splunk queries.
- Show leadership: stakeholder communication, timeline, ownership.
