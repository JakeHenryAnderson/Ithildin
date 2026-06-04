# SUB-GITMETA-002 Git Commit Metadata Workspace Scope

- Finding ID: SUB-GITMETA-002
- Severity: high
- Area: git commit metadata
- Affected files/functions: apps/api/src/ithildin_api/read_tools.py `ReadToolExecutor._commit_metadata_resource_from_arguments`; apps/api/src/ithildin_api/read_tools.py `GitReadTools.commit_metadata`; apps/api/src/ithildin_api/read_tools.py `GitReadTools._ensure_repo_toplevel_in_workspace`; tests/test_read_tools.py `test_git_commit_metadata_denies_parent_repo_outside_workspace`; tests/test_read_tools.py `test_git_commit_metadata_resource_denies_parent_repo_outside_workspace`
- Claim being tested: `git.show.commit_metadata` should not expose parent-repository metadata when the configured workspace root is a subdirectory inside a larger Git repository.
- Observed behavior: Internal xhigh source review found that running Git from a workspace subdirectory could resolve the parent repository and return changed-path metadata outside the configured workspace scope.
- Risk: A workspace configured inside a larger repository could let the agent infer parent-repo commit metadata and changed paths beyond the intended workspace boundary.
- Recommended fix: Fixed by resolving the Git toplevel for commit metadata and failing closed unless that toplevel is within or equal to the configured workspace root, both for runtime execution and resource construction.
- Blocking status: blocking
- Disposition: fixed
- Verification notes: `test_git_commit_metadata_denies_parent_repo_outside_workspace` verifies runtime denial for parent repos outside workspace scope. `test_git_commit_metadata_resource_denies_parent_repo_outside_workspace` verifies preview/resource construction marks the resource out of scope with a safe scope error.
