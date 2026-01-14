# Cloud Billing Automation

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

### Budget Monitoring

```bash
# Check budget status
cba budget status \
  --budget 10000 \
  --warning-threshold 80 \
  --critical-threshold 95

# Set up budget alerts
cba budget alerts \
  --emails devops@company.com \
  --webhook https://hooks.slack.com/webhook
```

### Resource Analysis

```bash
# Collect resource inventory
cba resources collect \
  --providers aws,azure

# Find idle resources
cba resources idle \
  --threshold-days 30

# Check tag compliance
cba resources compliance \
  --required-tags Environment,CostCenter,Owner
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
├── src/cloud_billing_automation/
│   ├── core/                    # Core infrastructure
│   │   ├── config.py           # Configuration management
│   │   ├── credentials.py      # Secure credential handling
│   │   └── exceptions.py       # Custom exceptions
│   ├── collectors/             # Data collection
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
│   ├── reports/                # Report generation
│   ├── utils/                  # Utilities
│   └── cli/                    # Command-line interface
├── tests/                      # Test suite
├── config/                     # Configuration examples
├── docs/                       # Documentation
└── examples/                   # Usage examples
```

## 🔧 Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/cloud_billing_automation

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
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

## 📊 Current Implementation Status

### ✅ Completed Features

- **Core Infrastructure**
  - ✅ Configuration management (YAML + environment variables)
  - ✅ Secure credential storage (encrypted keyring)
  - ✅ Comprehensive error handling
  - ✅ Project structure and packaging

- **Data Collection**
  - ✅ AWS billing data collection (Cost Explorer + resource APIs)
  - ✅ Azure billing data collection (Billing Management APIs)
  - ✅ GCP billing data collection (Cloud Billing APIs)
  - ✅ Standardized data structures across providers

- **Cost Analysis**
  - ✅ Comprehensive cost analysis and breakdown
  - ✅ Resource-level cost analysis with efficiency scoring
  - ✅ Advanced anomaly detection (multiple methods)
  - ✅ Trend analysis with seasonal pattern detection
  - ✅ Machine learning-based cost forecasting

### 🚧 In Progress

- **Budget Alerting System**
  - 🔄 Real-time budget monitoring
  - 🔄 Multi-channel alerting (email, webhooks)
  - 🔄 Escalation policies

### 📋 Planned Features

- **CLI Interface** - Command-line tool for automation
- **Tag Compliance** - Automated tag validation and enforcement
- **Idle Resource Detection** - Identify and report unused resources
- **Automated Reports** - Scheduled reports with multiple formats
- **CI/CD Integration** - Pipeline integration examples

## 🔐 Security Features

- **Encrypted Credential Storage** - All cloud credentials encrypted at rest
- **Secure Key Management** - Uses system keyring with Fernet encryption
- **IAM Best Practices** - Follows principle of least privilege
- **Audit Logging** - Comprehensive logging for security and compliance
- **No Hardcoded Secrets** - Configuration through secure channels

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📖 **Documentation**: [Full documentation](docs/)
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/NotHarshhaa/cloud-billing-automation/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/NotHarshhaa/cloud-billing-automation/discussions)
- 📧 **Email**: contact@example.com

## 🙏 Acknowledgments

- Built for the DevOps community to solve real-world cloud cost challenges
- Inspired by FinOps principles and cloud cost management best practices
- Thanks to all contributors who help make cloud cost management accessible

---

**⚡ Made with ❤️ for DevOps Engineers by DevOps Engineers**
