# Authentication

Workflows are using Github/AWS OpenID connect to perform the AWS
authentication ([refs](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)).  
If your repository needs to access AWS you will need to create a dedicated CI profile
in [infra-ci](https://github.com/sencrop/infra-ci).

# Standard workflows

## General purpose

### Version

This workflow will output a version for the current build:

- `sha` will compute the short git sha of the current commit
- `tag` will fetch the tag at the current commit

Typically `sha` versions are used for preproduction/staging while `tag` versions are used for production.

```yaml
jobs:
  version:
    uses: sencrop/github-workflows/.github/workflows/version-v3.yml@master
    with:
      from: sha | tag
```

You can use it in subsequent jobs using `${{ needs.version.outputs.version }}`
and `${{ needs.version.outputs.previous_version }}`.

### Release please

This workflow will trigger [release-please](https://github.com/googleapis/release-please).
Pull requests and commits will be performed by the [sencrop release bot](https://github.com/apps/sencrop-release-bot).

```
jobs:
  release-please:
    uses: sencrop/github-workflows/.github/workflows/release-please-v1.yml@master
    secrets: inherit
```

## Terraform workflows

These workflows are designed for generic terraform application code.
For ECS application managed by terraform you should look into [the dedicated workflows below](# ECS workflows).

### terraform-plan

Perform a terraform plan against `preproduction` and `production` environment and post the result to the pull request.

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

### terraform-deploy

This workflow wraps the same logic as `terraform-apply` but adds the deployment notification and tracking logic.

```yaml
jobs:
  infra:
    uses: sencrop/github-workflows/.github/workflows/terraform-deploy-v1.yml@master
    secrets: inherit
    with:
      application: my-application
      environment: preproduction or production
      version: new-version
```

## Docker workflows

### docker-push

This workflow build and push a docker image to an elastic container repository.

```yaml
jobs:
  image:
    uses: sencrop/github-workflows/.github/workflows/docker-push-v3.yml@master
    secrets: inherit
    with:
      image_name: your-image-name
      image_tag: your-image-tag
```

If you build often your docker image you might benefit from the built
in [cache management](https://docs.docker.com/build/ci/github-actions/cache/).

```yaml
    with:
      cache_docker_layers: true
```

### docker-tag

This workflow add a tag to an existing image in our elastic container repository.

```yaml
jobs:
  image:
    uses: sencrop/github-workflows/.github/workflows/docker-tag-v1.yml@master
    secrets: inherit
    with:
      image_name: your-image-name
      image_tag_from: the tag value of an existing image
      image_tag_to: the new tag value
```

### docker-experiment

This workflow build an experimental docker version and send the build ID to the github pull request.

```yaml
jobs:
  image:
    uses: sencrop/github-workflows/.github/workflows/docker-experiment-v1.yml@master
    secrets: inherit
    with:
      image_name: your-image-name
```

## ECS workflows

### terraform-plan-ecs

This is a more specialized version of the terraform plan workflow dedicated
to [standard ECS fargate service](https://github.com/sencrop/terraform-modules).  
The main difference is that this workflow will fetch the currrently deployed docker image tag version on aws and pass it
to the plan.

```yaml
jobs:
  terraform:
    uses: sencrop/github-workflows/.github/workflows/terraform-plan-ecs-v3.yml@master
    secrets: inherit
```

### ecs-deploy

This workflow will trigger a deployment of the given version of
a [standard ECS fargate application](https://github.com/sencrop/terraform-modules).
The outcome of the deployment will be notified on slack.

The infrastructure code must defined the deployed service in the `ecs_services` output.

```hcl
output "ecs_services" {
  value = ["svc1", "svc2"]
}
```

```yaml
jobs:
  deploy:
    uses: sencrop/github-workflows/.github/workflows/ecs-deploy-v3.yml@master
    secrets: inherit
    with:
      version: new-version
      environment: "preproduction or production"
      application: my-application
      slack_channel: my-ops-slack-channel
```

If your service uses a static docker image tag you may set the flag `use_version_as_docker_image_tag` to `false`.

### ecs-start

This workflow will start an ECS service. If the service is already running it has no effect.

```yaml
  start_service:
    uses: sencrop/github-workflows/.github/workflows/ecs-start-v2.yml@master
    secrets: inherit
    with:
      service: my-service
      environment: preproduction or production
```

### ecs-stop

This workflow will stop an ECS service. If the service is already stopped it has no effect.

```yaml
  stop_service:
    uses: sencrop/github-workflows/.github/workflows/ecs-stop-v2.yml@master
    secrets: inherit
    with:
      service: my-service
      environment: preproduction or production
```

### ecs-restart

This workflow will restart a running ECS service.

```yaml
  restart_service:
    uses: sencrop/github-workflows/.github/workflows/ecs-restart-v2.yml@master
    secrets: inherit
    with:
      service: my-service
      environment: preproduction or production
```

## Netlify workflows

### netlify-deploy

This workflow will deploy a web application to Netlify.

```yaml
jobs:
  deploy:
    uses: sencrop/github-workflows/.github/workflows/netlify-deploy-v1.yml@master
    secrets: inherit
    with:
      application: my-application
      version: version
      environment: staging or production
      s3_bucket: bucket where the artifacts are published (using the [upload-artifact](https://github.com/sencrop/github-workflows/blob/master/actions/upload-artifact/action.yaml) action)
```

### netlify-deploy-preview

This workflow will deploy a web application in preview mode to Netlify.

```yaml
jobs:
  deploy:
    uses: sencrop/github-workflows/.github/workflows/netlify-deploy-v1.yml@master
    secrets: inherit
    with:
      application: my-application
      version: version
      environment: staging or production
      s3_bucket: bucket where the artifacts are published (using the [upload-artifact](https://github.com/sencrop/github-workflows/blob/master/actions/upload-artifact/action.yaml) action)
```

## RDS workflows

### rds-start

This workflow will start a RDS instance. If the database instance is already running it has no effect.

```yaml
jobs:
  start_db:
    uses: sencrop/github-workflows/.github/workflows/rds-start-v2.yml@master
    secrets: inherit
    with:
      db_instance: my-instance-name
```

### rds-stop

This workflow will stop a RDS instance. If the database instance is already stopped it has no effect.

```yaml
jobs:
  db:
    uses: sencrop/github-workflows/.github/workflows/rds-stop-v2.yml@master
    secrets: inherit
    with:
      db_instance: my-instance-name
```

### node-module-cache

This action handles `node_modules` caching after installing dependencies for javascript projects. This has to be called
while merging a main branch so further GitHub action execution can benefit from this cache later on.

```yaml
---
name: Update node_modules cache

on:
  push:
    branches:
      - master
    paths:
      - package-lock.json
      - package.json
jobs:
  update_cache:
    uses: sencrop/github-workflows/.github/workflows/node_modules_cache-v1.yml@master
    secrets: inherit
    with:
      use_legacy_peer_deps: false
      use_ignore_scripts: true
```

Once the `node_modules` cache is filled in, it can be used later on to prevent unnecessary dependencies install
operations:

```yaml
  - name: Restore node_modules cache
    uses: actions/cache/restore@v4
    id: restore-cache
    with:
      path: "**/node_modules"
      key: ${{ runner.os }}-npm-${{ hashFiles('package-lock.json') }}
      restore-keys: ${{ runner.os }}-npm-

  - name: NPM CI Install
    if: steps.restore-cache.outputs.cache-hit != 'true'
    run: npm ci --ignore-scripts
    env:
      NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

## Standard actions

Standard actions can be reused in any custom or standard workflows.

### configure-aws-credentials

This action will authenticate the current CI wokrflow with AWS.
The variable `AWS_ACCOUNT_ID` is a global github variable accessible to all private repositories.
This action requires the `id-token: write` permission.

```yaml
jobs:
  my-job:
    permissions:
      id-token: write
    steps:
      - name: Configure aws credentials
        uses: sencrop/github-workflows/actions/configure-aws-credentials@master
        with:
          aws_account_id: ${{ vars.AWS_ACCOUNT_ID }}
```

### notify-deployment-in-progress

This action will notify in slack and in datadog that a deployment has been initiated for an application.

```yaml
jobs:
  my-job:
    steps:
      - name: Notify deployment in progress
        uses: sencrop/github-workflows/actions/notify-deployment-in-progress@master
        with:
          service: my-service
          environment: preproduction or production
          dd_api_key: ${{ secrets.DD_API_KEY }}
          current_version: version N-1
          deployed_version: version N
          slack_bot_token: ${{ secrets.SLACK_BOT_TOKEN }}
```

### track-deployment-time

This action will track in datadog the deployment time based on the duration the Github Action workflow.
This action requires the `actions: read` permission.

```yaml
jobs:
  permissions:
    actions: read
  my-job:
    steps:
      - name: Track deployment time
        uses: sencrop/github-workflows/actions/track-deployment-time@master
        with:
          service: my-service
          environment: preproduction or production
          dd_api_key: ${{ secrets.DD_API_KEY }}
```

### setup-terraform

This action setup terraform using the version defined in `main.tf`. The version must be strictly defined.

```yaml
jobs:
  my-job:
    permissions:
      contents: read
    steps:
      - name: Checkout
        uses: actions/checkout@v3
      - name: Terraform setup
        uses: sencrop/github-workflows/actions/setup-terraform@master
        with:
          working_directory: path/to/tf/directory
```
