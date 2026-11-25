#!/usr/bin/env bash
# Run on the server: write the app's .env from the AWS Secrets Manager secret, using the instance's IAM role.
# The server keeps its own POSTGRES_PASSWORD (it belongs to the existing database volume); a new one is made if missing.
#
#   AWS_REGION   default eu-north-1
#   SECRET_ID    default vst-creator/app
set -euo pipefail
cd "$(dirname "$0")/.."

REGION="${AWS_REGION:-eu-north-1}"
SECRET_ID="${SECRET_ID:-vst-creator/app}"

if ! command -v aws >/dev/null 2>&1; then
  echo "Installing the AWS CLI"
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq unzip curl >/dev/null
  tmp=$(mktemp -d)
  curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-$(uname -m).zip" -o "$tmp/aws.zip"
  unzip -q "$tmp/aws.zip" -d "$tmp"
  sudo "$tmp/aws/install" >/dev/null
  rm -rf "$tmp"
fi

umask 077
old_password=$(grep -s '^POSTGRES_PASSWORD=.' .env || true)
aws secretsmanager get-secret-value --region "$REGION" --secret-id "$SECRET_ID" \
  --query SecretString --output text > .env.new
echo >> .env.new
echo "${old_password:-POSTGRES_PASSWORD=$(openssl rand -hex 24)}" >> .env.new
mv .env.new .env
chmod 600 .env
echo "Wrote .env from secret $SECRET_ID"
