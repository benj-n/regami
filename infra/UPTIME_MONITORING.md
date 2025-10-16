# Uptime Monitoring Configuration

## Overview

External monitoring using UptimeRobot for 24/7 availability checks and instant alerting.

## UptimeRobot Configuration

### Account Setup

1. Sign up at https://uptimerobot.com (Free plan: 50 monitors)
2. Verify email
3. Configure alert contacts

### Monitor Configuration

#### 1. API Health Endpoint

```
Monitor Type: HTTP(S)
Friendly Name: Regami API - Health Check
URL: https://api.regami.com/health?check=db
Monitoring Interval: 5 minutes
Monitor Timeout: 30 seconds
HTTP Method: GET
Expected Status Code: 200

Alert Contacts:
- Email: devops@regami.com
- SMS: +33 X XX XX XX XX (for critical alerts)
- Slack: #alerts webhook
```

#### 2. Web Application

```
Monitor Type: HTTP(S)
Friendly Name: Regami Web App
URL: https://regami.com
Monitoring Interval: 5 minutes
Monitor Timeout: 30 seconds
HTTP Method: GET
Expected Status Code: 200
Keyword Monitoring: Check for "Regami" in response

Alert Contacts: Same as above
```

#### 3. Authentication Endpoint

```
Monitor Type: HTTP(S)
Friendly Name: Regami API - Auth
URL: https://api.regami.com/v1/auth/login
Monitoring Interval: 10 minutes
Monitor Timeout: 30 seconds
HTTP Method: POST
POST Value: {"email":"monitor@regami.com","password":"test"}
Expected Status Code: 401 (validates endpoint is responding)

Alert Contacts: Email only
```

#### 4. WebSocket Connectivity

```
Monitor Type: Port
Friendly Name: Regami WebSocket
URL/IP: api.regami.com
Port: 443
Monitoring Interval: 10 minutes

Alert Contacts: Email only
```

#### 5. Android APK Availability

```
Monitor Type: HTTP(S)
Friendly Name: Regami Android APK
URL: https://releases.regami.com/android/latest.apk
Monitoring Interval: 30 minutes
Expected Status Code: 200

Alert Contacts: Email only
```

### API Integration

```python
# backend/app/monitoring/uptimerobot.py
import requests
from typing import Dict, List

class UptimeRobotClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.uptimerobot.com/v2"

    def get_monitors(self) -> List[Dict]:
        """Get all monitors."""
        response = requests.post(
            f"{self.base_url}/getMonitors",
            data={
                "api_key": self.api_key,
                "format": "json"
            }
        )
        return response.json().get("monitors", [])

    def get_uptime_stats(self, monitor_id: str, days: int = 30) -> Dict:
        """Get uptime statistics for a monitor."""
        response = requests.post(
            f"{self.base_url}/getMonitors",
            data={
                "api_key": self.api_key,
                "monitors": monitor_id,
                "custom_uptime_ratios": str(days),
                "format": "json"
            }
        )
        return response.json()

    def pause_monitor(self, monitor_id: str) -> bool:
        """Pause monitoring (during maintenance)."""
        response = requests.post(
            f"{self.base_url}/editMonitor",
            data={
                "api_key": self.api_key,
                "id": monitor_id,
                "status": "0"  # 0 = paused, 1 = active
            }
        )
        return response.json().get("stat") == "ok"

    def create_monitor(self, name: str, url: str, interval: int = 300) -> Dict:
        """Create a new monitor."""
        response = requests.post(
            f"{self.base_url}/newMonitor",
            data={
                "api_key": self.api_key,
                "friendly_name": name,
                "url": url,
                "type": "1",  # HTTP(s)
                "interval": interval
            }
        )
        return response.json()
```

### Terraform Configuration

```hcl
# infra/aws/monitoring.tf

# SNS Topic for UptimeRobot alerts (via email)
resource "aws_sns_topic" "uptime_alerts" {
  name = "${var.app_name}-uptime-alerts"

  tags = {
    Name        = "${var.app_name}-uptime-alerts"
    Environment = var.environment
  }
}

resource "aws_sns_topic_subscription" "uptime_email" {
  topic_arn = aws_sns_topic.uptime_alerts.arn
  protocol  = "email"
  endpoint  = "devops@regami.com"
}

# Lambda function to process UptimeRobot webhooks
resource "aws_lambda_function" "uptimerobot_webhook" {
  filename      = "uptimerobot_webhook.zip"
  function_name = "${var.app_name}-uptimerobot-webhook"
  role          = aws_iam_role.lambda_uptimerobot.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 30

  environment {
    variables = {
      SLACK_WEBHOOK_URL = var.slack_webhook_url
      SNS_TOPIC_ARN     = aws_sns_topic.uptime_alerts.arn
    }
  }
}

# API Gateway for webhook endpoint
resource "aws_apigatewayv2_api" "webhook" {
  name          = "${var.app_name}-webhook-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "uptimerobot" {
  api_id           = aws_apigatewayv2_api.webhook.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.uptimerobot_webhook.invoke_arn
}

resource "aws_apigatewayv2_route" "uptimerobot" {
  api_id    = aws_apigatewayv2_api.webhook.id
  route_key = "POST /uptimerobot"
  target    = "integrations/${aws_apigatewayv2_integration.uptimerobot.id}"
}
```

### Slack Integration

```python
# lambda/uptimerobot_webhook/index.py
import json
import os
import boto3
from urllib.request import Request, urlopen

def handler(event, context):
    """Process UptimeRobot webhook and send to Slack."""

    # Parse webhook payload
    body = json.loads(event['body'])

    monitor_name = body.get('monitorFriendlyName')
    monitor_url = body.get('monitorURL')
    alert_type = body.get('alertType')  # 1 = down, 2 = up
    alert_details = body.get('alertDetails')

    # Determine color based on alert type
    color = "#ff0000" if alert_type == "1" else "#00ff00"
    status = "🔴 DOWN" if alert_type == "1" else "🟢 UP"

    # Create Slack message
    slack_message = {
        "attachments": [{
            "color": color,
            "title": f"{status} - {monitor_name}",
            "fields": [
                {"title": "URL", "value": monitor_url, "short": False},
                {"title": "Details", "value": alert_details, "short": False},
                {"title": "Time", "value": "<!date^{0}^{date_short_pretty} {time}|now>".format(int(time.time())), "short": True}
            ],
            "footer": "Regami Monitoring",
            "footer_icon": "https://regami.com/favicon.ico"
        }]
    }

    # Send to Slack
    slack_webhook_url = os.environ['SLACK_WEBHOOK_URL']
    req = Request(slack_webhook_url, json.dumps(slack_message).encode('utf-8'))
    req.add_header('Content-Type', 'application/json')
    urlopen(req)

    # Send to SNS (for email alerts)
    if alert_type == "1":  # Only email for downtime
        sns = boto3.client('sns')
        sns.publish(
            TopicArn=os.environ['SNS_TOPIC_ARN'],
            Subject=f"🔴 {monitor_name} is DOWN",
            Message=f"""
Monitor: {monitor_name}
URL: {monitor_url}
Status: DOWN
Details: {alert_details}

Check UptimeRobot dashboard for more information:
https://uptimerobot.com/dashboard
            """
        )

    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Webhook processed'})
    }
```

## Status Page

Create public status page at `status.regami.com`:

### UptimeRobot Public Status Page

1. Go to UptimeRobot Dashboard → Status Pages
2. Create New Status Page
3. Configure:
   - Page Name: "Regami Status"
   - Custom Domain: status.regami.com
   - Select monitors to display
   - Choose time ranges: 24h, 7d, 30d, 90d
   - Enable "Show uptime percentages"
   - Enable "Show response times"

### Custom Status Page (Alternative)

```html
<!-- status.html -->
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Regami - État des Services</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
        }
        .status-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            background-color: #f9fafb;
        }
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 10px;
        }
        .status-up { background-color: #10b981; }
        .status-down { background-color: #ef4444; }
        .status-degraded { background-color: #f59e0b; }
    </style>
</head>
<body>
    <h1>État des Services Regami</h1>
    <p>Statut en temps réel de nos services</p>

    <div id="status-container"></div>

    <script>
        async function loadStatus() {
            const response = await fetch('https://api.uptimerobot.com/v2/getMonitors', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    api_key: 'ur_readonly_api_key',
                    format: 'json'
                })
            });

            const data = await response.json();
            const container = document.getElementById('status-container');

            data.monitors.forEach(monitor => {
                const statusClass = monitor.status === 2 ? 'status-up' : 'status-down';
                const statusText = monitor.status === 2 ? 'Opérationnel' : 'Indisponible';

                container.innerHTML += `
                    <div class="status-item">
                        <div>
                            <span class="status-indicator ${statusClass}"></span>
                            ${monitor.friendly_name}
                        </div>
                        <div>${statusText}</div>
                    </div>
                `;
            });
        }

        loadStatus();
        setInterval(loadStatus, 60000); // Refresh every minute
    </script>
</body>
</html>
```

## Alert Configuration

### Alert Thresholds

- **Critical (Page team immediately)**:
  - API down for >2 minutes
  - Database health check failing
  - 5xx error rate >5%

- **Warning (Slack notification)**:
  - API response time >2 seconds
  - Uptime <99.9% over 24 hours
  - Single monitor failure (not affecting service)

- **Info (Email only)**:
  - Scheduled maintenance
  - Monitor recovered
  - Monthly uptime report

### On-Call Schedule

Use PagerDuty or UptimeRobot's alert contacts:

**Week 1:** Engineer A - Primary, Engineer B - Secondary
**Week 2:** Engineer B - Primary, Engineer C - Secondary
**Week 3:** Engineer C - Primary, Engineer A - Secondary
(Rotate weekly)

## Maintenance Windows

Pause monitors during planned maintenance:

```python
# scripts/maintenance_mode.py
from app.monitoring.uptimerobot import UptimeRobotClient

client = UptimeRobotClient(api_key=os.getenv("UPTIMEROBOT_API_KEY"))

# Pause all monitors
for monitor in client.get_monitors():
    client.pause_monitor(monitor['id'])

# Perform maintenance...

# Resume monitors
for monitor in client.get_monitors():
    client.resume_monitor(monitor['id'])
```

## Reporting

### Weekly Uptime Report

```python
# scripts/generate_uptime_report.py
import smtplib
from email.mime.text import MIMEText
from app.monitoring.uptimerobot import UptimeRobotClient

client = UptimeRobotClient(api_key=os.getenv("UPTIMEROBOT_API_KEY"))

# Get stats for all monitors
monitors = client.get_monitors()
report = []

for monitor in monitors:
    stats = client.get_uptime_stats(monitor['id'], days=7)
    uptime = stats['monitors'][0]['custom_uptime_ratio']

    report.append(f"{monitor['friendly_name']}: {uptime}%")

# Send email
msg = MIMEText("\n".join(report))
msg['Subject'] = 'Regami Weekly Uptime Report'
msg['From'] = 'monitoring@regami.com'
msg['To'] = 'team@regami.com'

s = smtplib.SMTP('localhost')
s.send_message(msg)
s.quit()
```

## Cost

**UptimeRobot Free Plan:**
- 50 monitors
- 5-minute interval
- Email/SMS/webhook alerts
- Public status page
- **Cost: $0/month**

**Pro Plan** ($7/month):
- 1-minute interval
- Unlimited alerts
- Custom status page domain
- Advanced statistics

## Next Steps

1. Create UptimeRobot account
2. Configure 5 primary monitors
3. Set up alert contacts (email, SMS, Slack)
4. Create public status page
5. Test alert notifications
6. Document on-call procedures
7. Schedule weekly uptime reviews

```
