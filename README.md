# github-workflows
Common Github Actions workflows

## terraform-plan

Perform a terraform plan  against `preproduction` and `production` environment and post the result to the pull request.

```yaml
jobs:
  terraform:
    uses: sencrop/github-workflows/.github/workflows/terraform-plan-v1.yml@master
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

If you need to use a private runner set `self_hosted` to `true`.

```yaml
    with:
      self_hosted: true
```


## terraform-plan-ecs

This is a more specialized version of the terraform plan workflow dedicated to [standard ECS fargate service](https://github.com/sencrop/terraform-modules).  
The main difference is that this workflow will fetch the currrently deployed docker image tag version on aws and pass it to the plan.


```yaml
jobs:
  terraform:
    uses: sencrop/github-workflows/.github/workflows/terraform-plan-ecs-v1.yml@master
    secrets: inherit
    with:
      service: "my-service"
      terraform_version: "1.2.9"

```

## ecs-deploy

This workflow will trigger a deployment of the given version of a [standard ECS fargate service](https://github.com/sencrop/terraform-modules).
The outcome of the deployment will be notified on slack.


```yaml
jobs:
  deploy:
    uses: sencrop/github-workflows/.github/workflows/ecs-deploy-v1.yml@master
    secrets: inherit
    with:
      docker_image_tag: "tag-from-the-build-step"
      environment: "preproduction pr production"
      terraform_version: "1.2.9"
      service: "my-service"
      slack_channel: "my-ops-slack-channel"
      notify_on_success: false
```
