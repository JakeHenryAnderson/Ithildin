# Attempt 008 API/UI Port-Release Attempt 002 Disposition

Status: `CONSUMED_COMPLETED`

Recovery `LV1-003-O4-ATTEMPT-008-PORT-RELEASE-002` completed successfully on exact
execution candidate commit `66b4c1ca66a142466a2b487941488c072c1ec4d0`, tree
`63bf4b6060a8e3082d1b5fdbeb2437f1b7236dcf`. This disposition records that historical
execution result; it does not rebind execution to the later closure candidate.

The exact Attempt 008 API container
`0bc38e9961ef6d190f5cc3d67b1c047077c2e143b541ee402032a06ecb292b85` and UI container
`5bc1d0a6d75db49d7501a8d1bdccc5ffe60d09ab54110d0a6eef6a99ca734d63` were running with
their exact reviewed images and loopback port mappings before the narrow stops. Both stop calls
returned zero; each container was then observed exited with an empty published-port projection.

The individual bind observations for ports 8000 and 5173 and the simultaneous port-set observation
confirm only point-in-time loopback availability. Future availability and generic port ownership
remain false. The result is not full project cleanup, Node revocation, or an enrollment
determination.

Node, Hermes, volumes, networks, images, and retained runtime and evidence are each
`not_targeted_by_recovery`. This is not an observed-unchanged claim and does not establish absence.
No container was deleted, Compose was not used, and no deletion or project-down authority existed.
No sealed private-directory leftover was observed after completion.

All five narrow granted authorities were exercised: retained-receipt validation, exact-project
container inspection, exact API/UI stop, point-in-time port-release observation, and private
receipt writing. Every false authority remained ungranted and unexercised.

The owner-only receipt root and journal are mode 0700 with uid 501 and gid 20; all twelve bound
leaves are mode 0600. The consumption receipt is
`sha256:9e6d32fe244fb1b98609561e617c0533700092139fc5ac1b6b70ef02aa8bff6f`;
the final disposition receipt is
`sha256:9a90ac1dca563f2117b1fed6a058b8f38d66e36928d063274bfd1a834d44d6ad`.
The JSON disposition binds those and all ten journal leaf sizes and hashes.

The budget is zero, consumption is true, retry authorization is false, and execution availability
is false. No successor O4 authority exists. The governed tool count remains 24. Release and UAT
remain false.
