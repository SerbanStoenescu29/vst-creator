#!/usr/bin/env bash
# Deploy vst-creator to the EC2 instance: pull the latest code from GitHub on the
# server, rebuild the Docker image and restart the container.
#
#   ./deploy-ec2.sh              deploy (uploads .env only if the server has none)
#   ./deploy-ec2.sh --env        deploy and overwrite the server's .env with the local one
#
# Settings (environment variables, all optional):
#   EC2_HOST      public IP/DNS of the instance (default: looked up with the AWS CLI)
#   INSTANCE_ID   used for the lookup        (default: i-02728519756f7ce97)
#   AWS_REGION    used for the lookup        (default: eu-north-1)
#   EC2_USER      SSH user                   (default: ubuntu)
#   SSH_KEY       private key                (default: ~/.ssh/vst-creator-ec2)
#   REPO_URL      repo to clone on the server
set -euo pipefail
cd "$(dirname "$0")"

INSTANCE_ID="${INSTANCE_ID:-i-02728519756f7ce97}"
AWS_REGION="${AWS_REGION:-eu-north-1}"
EC2_USER="${EC2_USER:-ubuntu}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/vst-creator-ec2}"
REPO_URL="${REPO_URL:-https://github.com/SerbanStoenescu29/vst-creator}"
APP_DIR="vst-creator"
FORCE_ENV=0
[ "${1:-}" = "--env" ] && FORCE_ENV=1

# The public IP changes every time the instance is stopped and started, so look it up.
if [ -z "${EC2_HOST:-}" ]; then
  if command -v aws >/dev/null 2>&1; then
    EC2_HOST=$(aws ec2 describe-instances --region "$AWS_REGION" --instance-ids "$INSTANCE_ID" \
      --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
  fi
  if [ -z "${EC2_HOST:-}" ] || [ "$EC2_HOST" = "None" ]; then
    echo "Could not find the instance's public IP (is it running?). Set EC2_HOST=<ip> and retry." >&2
    exit 1
  fi
fi
[ -f "$SSH_KEY" ] || { echo "SSH key not found: $SSH_KEY (set SSH_KEY=...)" >&2; exit 1; }
[ -f .env ] || { echo "No local .env to upload." >&2; exit 1; }

# The server pulls from GitHub, so unpushed commits would not be deployed.
if [ -n "$(git log '@{u}..' --oneline 2>/dev/null)" ]; then
  echo "Warning: you have local commits that are not pushed - the server will not get them." >&2
fi

SSH_OPTS=(-i "$SSH_KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15)
remote() { ssh "${SSH_OPTS[@]}" "$EC2_USER@$EC2_HOST" "$@"; }

echo "==> Deploying to $EC2_USER@$EC2_HOST"

echo "==> Installing Docker and fetching the code"
remote "set -e
  if ! command -v docker >/dev/null; then
    sudo apt-get update -qq
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq docker.io docker-compose-v2 >/dev/null
    sudo systemctl enable --now docker
  fi
  if [ -d $APP_DIR/.git ]; then git -C $APP_DIR pull -q --ff-only; else git clone -q $REPO_URL $APP_DIR; fi"

if [ "$FORCE_ENV" = 1 ] || ! remote "test -f $APP_DIR/.env"; then
  echo "==> Uploading .env"
  scp "${SSH_OPTS[@]}" .env "$EC2_USER@$EC2_HOST:$APP_DIR/.env"
  remote "chmod 600 $APP_DIR/.env"
fi

echo "==> Building and starting the container"
remote "cd $APP_DIR && sudo docker compose up -d --build 2>&1 | tail -5"

echo "==> Waiting for the app"
for _ in $(seq 1 20); do
  if remote "curl -fs localhost/healthz >/dev/null"; then
    echo "Deployed: http://$EC2_HOST/"
    exit 0
  fi
  sleep 3
done
echo "The app did not become healthy. Logs: ssh -i $SSH_KEY $EC2_USER@$EC2_HOST 'cd $APP_DIR && sudo docker compose logs --tail 50'" >&2
exit 1
