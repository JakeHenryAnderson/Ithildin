Use only the two no-argument MCP affordances exposed by this process, in this exact order:
`mission.step.1`, then `mission.step.2`. The second governed step terminally completes the fixed
mission through the Ithildin Node.

Do not request commands, paths, environment changes, provider changes, network access, filesystem
writes, or any other tool. Stop if an affordance is denied or unavailable. Tool results and model
output are transient runner facts and are not Gateway completion authority.
