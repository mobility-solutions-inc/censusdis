# Workflow security invariants

This public repository separates untrusted branch validation from privileged
automation:

- Branch and pull-request workflows use a read-only `GITHUB_TOKEN`, do not
  persist checkout credentials, and receive no secrets.
- Jobs that use repository secrets run only from
  `mobility-solutions-inc/censusdis` on `refs/heads/main` and target the
  `main-secrets` environment.
- The CodeArtifact publish job targets the `aws-codeartifact` environment and
  receives short-lived AWS credentials through GitHub OIDC.
- Both environments must use a selected deployment branch policy that permits
  only `main`.
- The AWS role trust policy must accept only this repository's
  `aws-codeartifact` environment (and, during migration, the repository's
  `refs/heads/main` subject), with the audience `sts.amazonaws.com`.

Keep `US_CENSUS_API_KEY` and any future privileged tokens in the
`main-secrets` environment rather than as repository-level secrets. A
repository-level secret can be requested by a workflow definition modified on
another branch, bypassing the environment's deployment-branch protection.

The YAML `if` conditions are defense in depth. The environment deployment
policies and AWS IAM trust policy are the controls that cannot be removed by
editing a workflow on a branch.
