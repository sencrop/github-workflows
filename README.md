# github-workflows
Common Github Actions workflows

## Authentication

Workflows v2 and above are using Github/AWS OpenID connect to perform the AWS authentication ([refs](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)).  
If your repository needs to access AWS you will need to create a dedicated CI profile in [infra-ci](https://github.com/sencrop/infra-ci).

## Standard workflows

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

### version

This workflow will output a version for the current build. It can be either based on the commit hash (default) or on the current tag.  
You can the get use the computed version in subsequent jobs using `${{ needs.version.outputs.version }}`.

```yaml
jobs:
  version:
    uses: sencrop/github-workflows/.github/workflows/version-v2.yml@master
```

If you want a versiom based on the current tag set `use_tags`.
```yaml
    with:
      use_tags: true
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

If you build often your docker image you might benefit from the built in [cache management](https://docs.docker.com/build/ci/github-actions/cache/).

```yaml
    with:
      cache_docker_layers: true
```

## ECS workflows

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


### ecs-start

This workflow will start an ECS service. If the service is already running it has no effect.

```yaml
  start_service:
    uses: sencrop/github-workflows/.github/workflows/ecs-start-v2.yml@master
    secrets: inherit
    with:
      service: my service
      environment: preproduction or production
```

### ecs-stop

This workflow will stop an ECS service. If the service is already stopped it has no effect.

```yaml
  stop_service:
    uses: sencrop/github-workflows/.github/workflows/ecs-stop-v2.yml@master
    secrets: inherit
    with:
      service: my service
      environment: preproduction or production
```

### ecs-restart

This workflow will restart a running ECS service.

```yaml
  restart_service:
    uses: sencrop/github-workflows/.github/workflows/ecs-restart-v2.yml@master
    secrets: inherit
    with:
      service: my service
      environment: preproduction or production
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
