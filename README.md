# stackwatch

> A CLI tool that monitors AWS CloudFormation stack drift and sends alerts to Slack or email.

---

## Installation

```bash
pip install stackwatch
```

Or install from source:

```bash
git clone https://github.com/youruser/stackwatch.git && cd stackwatch && pip install .
```

---

## Usage

Configure your credentials and notification targets via environment variables or a config file, then run:

```bash
stackwatch monitor --stack my-production-stack --alert slack
```

**Example with multiple stacks and email alerts:**

```bash
stackwatch monitor \
  --stack my-api-stack \
  --stack my-db-stack \
  --alert email \
  --interval 300
```

**Environment variables:**

| Variable | Description |
|---|---|
| `AWS_PROFILE` | AWS profile to use |
| `SLACK_WEBHOOK_URL` | Incoming webhook URL for Slack alerts |
| `ALERT_EMAIL` | Recipient address for email alerts |

Stackwatch will poll each stack at the specified interval (in seconds) and immediately notify you if drift is detected.

---

## Requirements

- Python 3.8+
- AWS credentials configured (`~/.aws/credentials` or environment variables)
- Boto3

---

## License

This project is licensed under the [MIT License](LICENSE).