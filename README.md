# github-workflows
Common Github Actions workflows

## authentication

Workflows v2 and above are using Github/AWS OpenID connect to perform the AWS authentication ([refs](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)).

## available workflows

### terraform-plan

Perform a terraform plan  against `preproduction` and `production` environment and post the result to the pull request.

```yaml
jobs:
  terraform:
    uses: sencrop/github-workflows/.github/workflows/terraform-plan-v2.yml@master
    secrets: inherit
    with:
      working_directory: ./terraform

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

For arguments non supported by default you should use the `extra_args` variable.

```yaml
  with:
    extra_args: -var-file=users.tfvars

```

### terraform-apply
Perform a terraform apply against the given environment.

```yaml
jobs:
  terraform:
    uses: sencrop/github-workflows/.github/workflows/terraform-apply-v2.yml@master
    secrets: inherit
    with:
      environment: "preproduction or production"
      working_directory: ./terraform

```


### terraform-plan-ecs

This is a more specialized version of the terraform plan workflow dedicated to [standard ECS fargate service](https://github.com/sencrop/terraform-modules).  
The main difference is that this workflow will fetch the currrently deployed docker image tag version on aws and pass it to the plan.


```yaml
jobs:
  terraform:
    uses: sencrop/github-workflows/.github/workflows/terraform-plan-ecs-v2.yml@master
    secrets: inherit
    with:
      service: my-service

```

### ecs-deploy

This workflow will trigger a deployment of the given version of a [standard ECS fargate service](https://github.com/sencrop/terraform-modules).
The outcome of the deployment will be notified on slack.


```yaml
jobs:
  deploy:
    uses: sencrop/github-workflows/.github/workflows/ecs-deploy-v2.yml@master
    secrets: inherit
    with:
      docker_image_tag: tag-from-the-build-step
      environment: "preproduction or production"
      service: my-service
      slack_channel: my-ops-slack-channel
```

### docker-push

This workflow build and push a docker image to an elastic container repository.

```yaml
jobs:
  image:
    uses: sencrop/github-workflows/.github/workflows/docker-push-v2.yml@master
    secrets: inherit
    with:
      docker_image_name: your-image-name
      docker_image_tag: your-image-tag
```
