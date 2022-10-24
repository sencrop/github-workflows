# github-workflows
Common Github Actions workflows

## terraform-plan

Perform a terraform plan  against `preproduction` and `production` environment and post the result to the pull request.

```yaml
jobs:
  terraform:
    uses: sencrop/github-workflows/.github/workflows/terraform-plan-v1.yml
    secrets: inherit
    with:
      terraform_version: "1.2.9"
      working_directory: "./terraform"

```

The list of environment can be overrided using the `environment` variable.

```yaml
    with:
      environments: "['preproduction']"
```

## terraform-plan-ecs

This is a more specialized version of the terraform plan workflow dedicated to [standard ECS fargate service](https://github.com/sencrop/terraform-modules).  
The main is that difference is that it will get the currrently deployed docker image tag version on aws and pass it to the plan.


```yaml
jobs:
  terraform:
    uses: sencrop/github-workflows/.github/workflows/terraform-plan-ecs-v1.yml
    secrets: inherit
    with:
      service: "my-service"
      terraform_version: "1.2.9"

```
