# Cloud Billing Automation

![banner](https://imgur.com/WZ3x1wq.png)

👷‍♂️ **DevOps-Centric Cloud Cost Governance & Automation**

A comprehensive cloud billing automation tool built for Cloud Engineers and DevOps Engineers to gain visibility, control, and automation over cloud billing across AWS, Azure, and GCP.

## 🎯 Why DevOps & Cloud Engineers Use This

- 🚨 **Prevent unexpected cloud bills** with real-time monitoring and alerts
- 🤖 **Automate cloud cost monitoring** through scheduled jobs and CI/CD integration
- 🏷️ **Enforce tagging & cost ownership** with automated compliance checks
- 🔍 **Detect cost anomalies early** using machine learning-based anomaly detection
- ⚙️ **Integrate billing checks into automation workflows** with CLI and API access

## ✨ Core DevOps Features

### ☁️ **Multi-Cloud Support**
- **AWS**: Cost Explorer, EC2, RDS, Lambda, S3 integration
- **Azure**: Billing Management, Resource Manager, Compute, Storage APIs
- **GCP**: Cloud Billing, Compute Engine, Cloud Storage integration

### 📊 **Cost Analysis & Insights**
- **Cost breakdown** by service, region, environment, and cost center
- **Resource-level analysis** with efficiency scoring and recommendations
- **Trend analysis** with seasonal pattern detection
- **Advanced forecasting** using machine learning models

### 🚨 **Intelligent Alerting**
- **Budget threshold monitoring** with configurable warning and critical levels
- **Anomaly detection** using Z-score, IQR, and percentage deviation methods
- **Multi-channel notifications** (email, webhooks, Slack integration)
- **Escalation policies** for critical alerts

### 🏷️ **Tag Compliance & Governance**
- **Automated tag validation** for required tags (Environment, CostCenter, etc.)
- **Cost ownership tracking** through mandatory tagging policies
- **Compliance reporting** with violation detection and remediation suggestions

### 🔍 **Resource Optimization**
- **Idle resource detection** for compute instances, storage, and databases
- **Cost optimization recommendations** based on usage patterns
- **Rightsizing suggestions** with potential savings calculations

### 📑 **Automated Reporting**
- **Scheduled reports** (daily, weekly, monthly) in multiple formats
- **Custom report templates** with charts and visualizations
- **Email delivery** with interactive HTML reports

### ⚙️ **DevOps Integration**
- **CLI tool** for automation and scripting
- **YAML configuration** for infrastructure-as-code compatibility
- **CI/CD pipeline integration** examples
- **Cron job scheduling** for automated monitoring

## 🛠️ Tech Stack

- **Python 3.8+** - Core automation framework
- **Cloud SDKs** - boto3 (AWS), azure-mgmt, google-cloud
- **Data Processing** - pandas, numpy for analysis
- **Machine Learning** - scikit-learn for forecasting
- **Security** - cryptography, keyring for credential management
- **CLI** - Click, Typer, Rich for command-line interface
- **Configuration** - YAML for declarative config

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Cloud provider credentials (AWS, Azure, or GCP)
- Required billing permissions in your cloud accounts

### Installation

```bash
# Clone the repository
git clone https://github.com/NotHarshhaa/cloud-billing-automation.git
cd cloud-billing-automation

# Install in development mode
pip install -e .

# Or install from requirements
pip install -r requirements.txt
```

### Configuration

Create a configuration file:

```yaml
# config/billing-config.yaml
debug: false
log_level: "INFO"
data_retention_days: 90

providers:
  aws:
    enabled: true
    account_id: "123456789012"
    regions: ["us-east-1", "us-west-2"]
    tags_required: ["Environment", "CostCenter", "Owner"]
    cost_center_tag: "CostCenter"
    environment_tag: "Environment"
  
  azure:
    enabled: false
    subscription_id: "your-subscription-id"
    regions: ["eastus", "westus2"]
    tags_required: ["Environment", "CostCenter"]
  
  gcp:
    enabled: false
    project_id: "your-gcp-project"
    regions: ["us-central1", "us-east1"]
    tags_required: ["Environment", "CostCenter"]

budget:
  monthly_limit: 10000.0
  warning_threshold: 0.8  # 80%
  critical_threshold: 0.95  # 95%
  currency: "USD"
  alert_emails: ["devops@company.com"]
  alert_webhooks: ["https://hooks.slack.com/your-webhook"]

reports:
  output_dir: "reports"
  formats: ["json", "csv", "html"]
  schedule: "daily"
  include_charts: true
  email_reports: true
  email_recipients: ["finance@company.com"]
```

### Setup Credentials

```bash
# AWS credentials
cba credentials setup-aws \
  --access-key-id YOUR_ACCESS_KEY \
  --secret-access-key YOUR_SECRET_KEY

# Azure service principal
cba credentials setup-azure \
  --tenant-id YOUR_TENANT_ID \
  --client-id YOUR_CLIENT_ID \
  --client-secret YOUR_CLIENT_SECRET \
  --subscription-id YOUR_SUBSCRIPTION_ID

# GCP service account
cba credentials setup-gcp \
  --service-account-key-path /path/to/service-account.json
```

## � Alerting & Notification System

The cloud-billing-automation tool includes a comprehensive alerting system with multi-channel notifications, escalation policies, and intelligent alert management.

### **Alert Types**

- **Budget Alerts** - Threshold-based budget monitoring (warning, critical, exceeded)
- **Forecast Alerts** - Predictive alerts based on spending trends
- **Anomaly Alerts** - Statistical detection of cost outliers
- **Trend Alerts** - Spending pattern changes and escalations
- **Resource Alerts** - Individual resource cost issues

### **Notification Channels**

- **Email** - Rich HTML emails with detailed information and recommendations
- **Slack** - Color-coded messages with interactive elements
- **Webhook** - JSON payloads for integration with monitoring systems
- **Custom Channels** - Extensible channel system for custom integrations

### **Alert Features**

- **Severity Levels** - Low, Medium, High, Critical with appropriate escalation
- **Cooldown Periods** - Prevent alert spam with configurable cooldowns
- **Alert Suppression** - Temporary suppression for maintenance windows
- **Template System** - Jinja2-based dynamic alert templates
- **Alert History** - Comprehensive tracking and analytics
- **Smart Grouping** - Reduces noise by grouping related alerts

### **Escalation Policies**

- **Threshold-Based** - Different actions for different severity levels
- **Multi-Channel Routing** - Critical alerts go to all channels, warnings to email only
- **Time-Based Escalation** - Escalate unacknowledged critical alerts
- **Auto-Resolution** - Automatically resolve alerts when conditions normalize

## 🖥️ CLI Interface

The cloud-billing-automation tool includes a comprehensive command-line interface with rich output, intuitive commands, and professional error handling.

### **Installation & Setup**

```bash
# Install the tool
pip install cloud-billing-automation

# Initialize configuration
cba init --output-dir config

# Set up credentials
cba credentials setup-aws --access-key-id YOUR_KEY --secret-access-key YOUR_SECRET
cba credentials setup-azure --tenant-id TENANT_ID --client-id CLIENT_ID --client-secret SECRET --subscription-id SUB_ID
cba credentials setup-gcp --service-account-key-path /path/to/key.json

# Validate credentials
cba credentials validate
cba credentials status

# List stored credentials
cba credentials list

# Export credentials
cba credentials export aws --output-file aws-credentials.sh
```

### **Command Structure**

```bash
cba [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]

Global Options:
  -c, --config FILE     Configuration file path
  --debug              Enable debug mode
  -v, --verbose        Enable verbose output
  --help               Show help message
```

### **Cost Analysis Commands**

```bash
# Analyze costs for specific period
cba analyze costs \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --providers aws,azure \
  --output table

# Get cost breakdown by service
cba analyze breakdown \
  --group-by service \
  --period monthly

# Detect cost anomalies
cba analyze anomalies \
  --methods zscore,iqr,percentage \
  --threshold 2.0

# Analyze cost trends
cba analyze trends \
  --metrics total_cost \
  --period weekly

# Generate cost forecast
cba analyze forecast \
  --days 30 \
  --model auto
```

### **Budget Management Commands**

```bash
# Check current budget status
cba budget status \
  --config config/billing-config.yaml \
  --forecast

# Set monthly budget limit
cba budget set-limit 10000

# Set up budget alerts
cba budget alerts --setup

# Test alert channels
cba budget alerts --test

# View budget history
cba budget history --days 30

# Generate budget forecast
cba budget forecast --days 30
```

### **Alert Management Commands**

```bash
# Test notification channels
cba alerts test \
  --channels email,slack,webhook

# View alert history
cba alerts history \
  --days 30 \
  --severity critical,high \
  --status active

# Suppress alerts for maintenance
cba alerts suppress \
  --resource-id i-1234567890abcdef0 \
  --duration-hours 12 \
  --reason "Scheduled maintenance"

# Acknowledge an alert
cba alerts acknowledge alert-id-123 --by "John Doe"

# Resolve an alert
cba alerts resolve alert-id-123

# Check alert system status
cba alerts status

# Manage alert rules
cba alerts rules --list
cba alerts rules --enable budget_warning
cba alerts rules --disable anomaly_detection
```

### **CLI Features**

- **Rich Terminal Output** - Beautiful tables, panels, and colored output
- **Progress Indicators** - Progress bars for long-running operations
- **Error Handling** - User-friendly error messages and validation
- **Auto-completion** - Command auto-completion (bash/zsh)
- **Help System** - Comprehensive help for all commands
- **Configuration Detection** - Automatic config file discovery
- **Multiple Output Formats** - Table, JSON, CSV output options

### **Output Examples**

#### Budget Status Output
```
Checking budget status...

Budget Status - Warning
┌─────────────────┬──────────────┐
│ Metric          │ Value        │
├─────────────────┼──────────────┤
│ Budget Limit    │ $10,000.00   │
│ Current Spend   │ $8,234.56    │
│ Usage           │ 82.3%        │
│ Remaining       │ $1,765.44    │
│ Days Remaining  │ 12           │
└─────────────────┴──────────────┘

Risk Assessment
─────────────────────────────────
Risk Level: HIGH
Daily Average: $274.49
Projected Daily: $147.11
```

#### Alert History Output
```
Loading alert history for last 30 days...

Alert History (15 alerts)
┌──────────┬─────────────────────────────┬──────────┬──────────────┬─────────┬─────────────────────┐
│ ID       │ Title                        │ Severity │ Status       │ Source  │ Time                │
├──────────┼─────────────────────────────┼──────────┼──────────────┼─────────┼─────────────────────┤
│ 1234...  │ Budget Warning: 82.3% used   │ medium   │ active       │ Budget  │ 2024-01-15 14:30    │
│ 5678...  │ Cost Anomaly Detected        │ high     │ resolved     │ Anomaly │ 2024-01-14 09:15    │
│ 9012...  │ Budget Critical: 95.1% used  │ critical │ acknowledged │ Budget  │ 2024-01-13 16:45    │
└──────────┴─────────────────────────────┴──────────┴──────────────┴─────────┴─────────────────────┘
```

## 📖 Usage Examples

### Basic Cost Analysis

```bash
# Analyze costs for the last 30 days
cba analyze costs \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --config config/billing-config.yaml

# Get cost breakdown by service
cba analyze breakdown \
  --group-by service \
  --period monthly

# Detect cost anomalies
cba analyze anomalies \
  --methods zscore,iqr,percentage \
  --threshold 2.0
```

### Budget Monitoring & Alerting

```bash
# Check budget status
cba budget status \
  --config config/billing-config.yaml

# Set up budget alerts with multiple channels
cba budget alerts setup \
  --emails devops@company.com,finance@company.com \
  --slack-webhook https://hooks.slack.com/your-webhook \
  --webhook https://monitoring.company.com/webhooks/billing

# Test alert channels
cba alerts test \
  --channels email,slack,webhook

# View alert history
cba alerts history \
  --days 30 \
  --severity critical,high

# Suppress alerts for maintenance
cba alerts suppress \
  --resource-id i-1234567890abcdef0 \
  --duration-hours 12 \
  --reason "Scheduled maintenance"
```

### Alert Configuration Examples

```yaml
# config/alerts.yaml
notifications:
  channels:
    email:
      type: email
      smtp_server: smtp.company.com
      smtp_port: 587
      username: alerts@company.com
      password: ${EMAIL_PASSWORD}
      from_email: alerts@company.com
      to_emails: 
        - devops@company.com
        - finance@company.com
      use_tls: true
    
    slack:
      type: slack
      webhook_url: ${SLACK_WEBHOOK_URL}
      channel: "#billing-alerts"
      username: "CloudBillingBot"
      icon_emoji: ":moneybag:"
    
    webhook:
      type: webhook
      url: https://monitoring.company.com/webhooks/billing
      method: POST
      headers:
        Authorization: "Bearer ${WEBHOOK_TOKEN}"
        Content-Type: "application/json"
      timeout: 30
      retry_count: 3

  alert_rules:
    budget_warning:
      enabled: true
      severity: medium
      cooldown_period: 60  # minutes
      channels: [email, slack]
    
    budget_critical:
      enabled: true
      severity: high
      cooldown_period: 30
      channels: [email, slack, webhook]
    
    anomaly_detection:
      enabled: true
      min_confidence: 0.7
      min_deviation_percentage: 20.0
      channels: [email]
```

### Configuration Management

```bash
# Create configuration file
cba config create --template production --output-file billing-config.yaml

# Validate configuration
cba config validate --config billing-config.yaml

# Show current configuration
cba config show --section providers

# Edit configuration interactively
cba config edit --section budget

# Merge configurations
cba config merge source-config.yaml --target-file billing-config.yaml --strategy merge
```

### Reporting

```bash
# Generate monthly report
cba reports generate \
  --period monthly \
  --formats html,pdf \
  --email finance@company.com

# Schedule daily reports
cba reports schedule \
  --frequency daily \
  --time 09:00 \
  --recipients team@company.com
```

## 🏗️ Architecture

```
cloud-billing-automation/
├── cloud_billing_automation/     # Main package
│   ├── core/                     # Core infrastructure
│   │   ├── config.py            # Configuration management
│   │   ├── credentials.py      # Secure credential handling
│   │   └── exceptions.py       # Custom exceptions
│   ├── collectors/              # Data collection
│   │   ├── base.py            # Base collector interface
│   │   ├── aws_collector.py   # AWS billing data
│   │   ├── azure_collector.py # Azure billing data
│   │   └── gcp_collector.py   # GCP billing data
│   ├── analyzers/              # Cost analysis
│   │   ├── cost.py            # Cost analysis & breakdown
│   │   ├── anomaly.py         # Anomaly detection
│   │   ├── trend.py           # Trend analysis
│   │   └── forecast.py        # Cost forecasting
│   ├── alerts/                 # Alerting system
│   │   ├── base.py            # Base alert management
│   │   ├── budget.py          # Budget alert manager
│   │   ├── anomaly.py         # Anomaly alert manager
│   │   ├── channels.py        # Notification channels
│   │   └── templates.py       # Alert templates
│   ├── reports/                # Report generation
│   ├── utils/                  # Security and utility modules
│   ├── security.py         # IAM and access control
│   ├── encryption.py        # Data encryption utilities
│   ├── validation.py        # Input validation and sanitization
│   └── helpers.py           # Formatting and data utilities
│   ├── cli/                    # Command-line interface
│   │   ├── main.py            # Main CLI application
│   │   └── commands/          # CLI command modules
│   │       ├── analyze.py     # Cost analysis commands
│   │       ├── budget.py      # Budget monitoring commands
│   │       ├── alerts.py      # Alert management commands
│   │       ├── resources.py   # Resource commands (planned)
│   │       ├── reports.py     # Report commands (planned)
│   │       ├── credentials.py # Credential management commands
│   │       └── config.py      # Configuration management commands
├── tests/                      # Test suite
├── config/                     # Configuration examples
├── docs/                       # Documentation
├── examples/                   # Usage examples
├── pyproject.toml             # Project configuration
├── requirements.txt           # Dependencies
├── setup.py                   # Setup script
└── README.md                  # This file
```

## 🔧 Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=cloud_billing_automation

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
```

### Code Quality

```bash
# Format code
black . tests/

# Lint code
flake8 . tests/

# Type checking
mypy .
```

### Adding New Cloud Providers

1. Create a new collector class inheriting from `BaseCollector`
2. Implement required abstract methods:
   - `authenticate()`
   - `collect_billing_data()`
   - `collect_resource_data()`
   - `get_cost_breakdown()`
3. Add provider configuration to `Config` class
4. Update CLI commands and documentation

### Adding New CLI Commands

1. Create a new command module in `cli/commands/`
2. Inherit from `typer.Typer` for command structure
3. Implement command logic with proper error handling
4. Add rich output formatting using `rich.console.Console`
5. Register the command in the main CLI app

### Adding New Alert Channels

1. Create a new channel class inheriting from `BaseChannel`
2. Implement `send()` and `test_connection()` methods
3. Add channel type to `ChannelManager._initialize_channels()`
4. Create alert templates for the new channel
5. Update configuration schema

## 📊 Current Implementation Status

### ✅ **Completed Features**

- **Core Infrastructure**
  - ✅ Configuration management (YAML + environment variables)
  - ✅ Secure credential storage (encrypted keyring)
  - ✅ Comprehensive error handling
  - ✅ Project structure and packaging

- **Data Collection & Analysis**
  - ✅ Multi-cloud billing data collection (AWS, Azure, GCP)
  - ✅ Cost analysis and breakdown by multiple dimensions
  - ✅ Anomaly detection with statistical methods
  - ✅ Trend analysis and forecasting
  - ✅ Resource-level cost analysis

- **Budget Monitoring & Alerting**
  - ✅ Budget threshold monitoring and alerts
  - ✅ Multi-channel notifications (Email, Slack, Webhook)
  - ✅ Alert escalation policies and suppression
  - ✅ Dynamic alert templates (Jinja2)
  - ✅ Real-time monitoring and history tracking

- **CLI Interface**
  - ✅ Rich terminal output with tables and progress bars
  - ✅ Comprehensive command structure (analyze, budget, alerts)
  - ✅ Professional error handling and validation
  - ✅ Interactive configuration management
  - ✅ Credential management commands

- **IAM & Security**
  - ✅ Role-based access control (RBAC)
  - ✅ JWT-based session management
  - ✅ Secure credential encryption (AES-256)
  - ✅ Comprehensive audit logging
  - ✅ Multi-cloud validation and sanitization
  - ✅ Security utilities and helper functions

### 🚧 In Progress

- **Tag Compliance** - Automated tag validation and enforcement (next priority)

### 📋 Planned Features

- **Idle Resource Detection** - Identify and report unused resources
- **Automated Reports** - Scheduled reports with multiple formats
- **CI/CD Integration** - Pipeline integration examples

## 🔐 Security Features

- **Role-Based Access Control (RBAC)** - Granular permissions with roles (admin, operator, viewer, billing_manager, devops)
- **JWT Session Management** - Secure token-based authentication with configurable timeouts
- **AES-256 Encryption** - Military-grade encryption for all sensitive data and credentials
- **Comprehensive Audit Logging** - Complete audit trail for all security events and operations
- **Multi-Cloud Validation** - Input validation and sanitization for AWS, Azure, and GCP
- **Security Utilities** - Password hashing, IP validation, secure file operations
- **Account Lockout** - Automatic account lockout after failed login attempts
- **Session Revocation** - Immediate session termination capabilities
- **Secure Key Storage** - Encrypted key management with restrictive file permissions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🛠️ Author & Community

Built with passion and purpose by [**Harshhaa**](https://github.com/NotHarshhaa).  
Your ideas, feedback, and contributions are what make this project better.

⚡ **Made with ❤️ for DevOps Engineers by Harshhaa**

**Connect & Collaborate:**  

* **GitHub:** [@NotHarshhaa](https://github.com/NotHarshhaa)  
* **Links:** [Links - Portfolio](https://link.notharshhaa.site)  
* **Portfolio:** [Portfolio](https://notharshhaa.site)  
* **CV Portfolio:** [CV Portfolio](https://cv.notharshhaa.site)
* **LinkedIn:** [Harshhaa Vardhan Reddy](https://www.linkedin.com/in/harshhaa-vardhan-reddy/)  

---

## ⭐ How You Can Support

If you found this project useful:  

* ⭐ **Star** the repository to show your support  
* 📢 **Share** it with your friends and colleagues  
* 📝 **Open issues** or **submit pull requests** to help improve it

---

### 📢 Stay Connected

[![Follow Me](https://imgur.com/2j7GSPs.png)](https://github.com/NotHarshhaa)

Join the community, share your experience, and help us grow!
