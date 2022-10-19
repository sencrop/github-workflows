# github-workflows
Common Github Actions workflows

## terraform-plan-ecs

Perform a terraform plan against preprod and prod deplyoment for a [standard ECS fargate service](https://github.com/sencrop/terraform-modules).

```yaml
jobs:
  terraform:
    uses: sencrop/github-workflows/.github/workflows/terraform-plan-ecs-v1.yml
    secrets: inherit
    with:
      service: "my-service"
      terraform_version: "1.2.9"

```

If the application is deployed on a single environment you can override the list of environments.

```yaml
    with:
      environments: "['preproduction']"
```
