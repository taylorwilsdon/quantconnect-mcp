<div align="center">

# ◆ QuantConnect MCP Server

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://python.org)
[![FastMCP](https://img.shields.io/badge/FastMCP-v2.7%2B-green.svg)](https://github.com/fastmcp/fastmcp)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/Code%20Style-Black-black.svg)](https://github.com/psf/black)
[![Type Checked](https://img.shields.io/badge/Type%20Checked-mypy-blue.svg)](https://mypy.readthedocs.io/)

**Professional-grade Model Context Protocol server for QuantConnect's algorithmic trading platform**

*Seamlessly integrate QuantConnect's research environment, statistical analysis, and portfolio optimization into your AI workflows*

<a href="https://glama.ai/mcp/servers/@taylorwilsdon/quantconnect-mcp">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@taylorwilsdon/quantconnect-mcp/badge" alt="QuantConnect Server MCP server" />
</a>

[◉ Quick Start](#-quick-start) •
[◉ Documentation](#-comprehensive-api-reference) •
[◉ Architecture](#-architecture) •
[◉ Contributing](#-contributing)

</div>

---

## ◈ Why QuantConnect MCP Server?

Transform your algorithmic trading research with a **production-ready MCP server** that provides:

- **⚙ Research Environment**: Full QuantBook integration for interactive financial analysis
- **◆ Advanced Analytics**: PCA, cointegration testing, mean reversion analysis, and correlation studies  
- **↗ Portfolio Optimization**: Sophisticated sparse optimization with Huber Downward Risk minimization
- **◎ Universe Selection**: ETF constituent analysis and multi-criteria asset screening
- **▪ Enterprise Security**: SHA-256 authenticated API integration with QuantConnect
- **⚡ High Performance**: Async-first design with concurrent data processing

## ◈ Table of Contents

- [◈ Quick Start](#-quick-start)
- [◈ Installation](#-installation)
- [◈ Authentication](#-authentication)
- [◈ Usage Examples](#-usage-examples)
- [◈ Comprehensive API Reference](#-comprehensive-api-reference)
- [◈ Architecture](#-architecture)
- [◈ Advanced Configuration](#-advanced-configuration)
- [◈ Testing](#-testing)
- [◈ Contributing](#-contributing)
- [◈ License](#-license)

## ◈ Quick Start

Get up and running in under 2 minutes:

### 1. **Install with uvx (Recommended)**
```bash
# Install and run directly from PyPI - no cloning required!
uvx quantconnect-mcp

# Or install with uv/pip
uv pip install quantconnect-mcp
pip install quantconnect-mcp
```

### 2. **Set Up QuantConnect Credentials**
```bash
export QUANTCONNECT_USER_ID="your_user_id"
export QUANTCONNECT_API_TOKEN="your_api_token"
export QUANTCONNECT_ORGANIZATION_ID="your_org_id"  # Optional
```

### 3. **Launch the Server**
```bash
# STDIO transport (default) - Recommended for MCP clients
uvx quantconnect-mcp

# HTTP transport
MCP_TRANSPORT=streamable-http MCP_PORT=8000 uvx quantconnect-mcp
```

### 4. **Start Analyzing**
```python
# Initialize research environment
await initialize_quantbook(instance_name="research")

# Add securities for analysis
await add_multiple_equities(["AAPL", "MSFT", "GOOGL", "AMZN"], resolution="Daily")

# Perform sophisticated analysis
await perform_pca_analysis(
    symbols=["AAPL", "MSFT", "GOOGL", "AMZN"],
    start_date="2023-01-01",
    end_date="2024-01-01"
)
```

## ◈ Installation

### Prerequisites

- **Python 3.12+** (Type-annotated for maximum reliability)
- **Active QuantConnect Account** with API access
- **uv** (recommended) or pip package manager

### Installation Methods

#### Method 1: uvx (Recommended)
```bash
# No installation needed - run directly from PyPI
uvx quantconnect-mcp

# uvx automatically handles all dependencies and isolation
```

#### Method 2: Global Installation
```bash
# Using uv (fastest)
uv pip install quantconnect-mcp

# Using pip
pip install quantconnect-mcp

# Then run with:
quantconnect-mcp
```

#### Method 3: Development Installation
```bash
# Clone for development
git clone https://github.com/your-org/quantconnect-mcp
cd quantconnect-mcp

# Install with development dependencies
uv sync --dev

# Run locally
uv run quantconnect_mcp/main.py
```

### Verify Installation

```bash
# Check if the package is working
uvx quantconnect-mcp --help

# Test API connectivity (requires credentials)
quantconnect-mcp
```

## ◈ Authentication

### Getting Your Credentials

| Credential | Where to Find | Required |
|------------|---------------|----------|
| **User ID** | Email received when signing up | ◉ Yes |
| **API Token** | [QuantConnect Settings](https://www.quantconnect.com/settings/) | ◉ Yes |
| **Organization ID** | Organization URL: `/organization/{ID}` | ◦ Optional |

### Configuration Methods

#### Method 1: Environment Variables (Recommended)
```bash
# Add to your .bashrc, .zshrc, or .env file
export QUANTCONNECT_USER_ID="123456"
export QUANTCONNECT_API_TOKEN="your_secure_token_here"
export QUANTCONNECT_ORGANIZATION_ID="your_org_id"  # Optional
```

#### Method 2: Runtime Configuration
```python
# Configure programmatically
await configure_quantconnect_auth(
    user_id="123456",
    api_token="your_secure_token_here",
    organization_id="your_org_id"  # Optional
)

# Validate configuration
result = await validate_quantconnect_auth()
print(f"Auth Status: {result['authenticated']}")
```

#### Method 3: Interactive Setup
```python
# Check current status
status = await get_auth_status()

# Test API connectivity
test_result = await test_quantconnect_api()
```

## ◈ Usage Examples

### Financial Research Pipeline

```python
# 1. Initialize research environment
await initialize_quantbook(instance_name="research_2024")

# 2. Build universe from ETF constituents
await add_etf_universe_securities(
    etf_ticker="QQQ",
    date="2024-01-01",
    resolution="Daily"
)

# 3. Perform correlation analysis
correlation_matrix = await calculate_correlation_matrix(
    symbols=["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"],
    start_date="2023-01-01",
    end_date="2024-01-01"
)

# 4. Find uncorrelated assets for diversification
uncorrelated = await select_uncorrelated_assets(
    symbols=correlation_matrix["symbols"],
    num_assets=5,
    method="lowest_correlation",
    start_date="2023-01-01",
    end_date="2024-01-01"
)

# 5. Optimize portfolio with advanced algorithm
optimized_portfolio = await sparse_optimization(
    portfolio_symbols=uncorrelated["selected_assets"]["symbols"],
    benchmark_symbol="SPY",
    start_date="2023-01-01",
    end_date="2024-01-01",
    max_weight=0.15,
    lambda_param=0.01
)
```

### Statistical Analysis Workflow

```python
# Cointegration analysis for pairs trading
cointegration_result = await test_cointegration(
    symbol1="KO",
    symbol2="PEP",
    start_date="2023-01-01",
    end_date="2024-01-01",
    trend="c"
)

if cointegration_result["is_cointegrated"]:
    print(f"◉ Cointegration detected (p-value: {cointegration_result['cointegration_pvalue']:.4f})")
    
    # Analyze mean reversion opportunities
    mean_reversion = await analyze_mean_reversion(
        symbols=["KO", "PEP"],
        start_date="2023-01-01",
        end_date="2024-01-01",
        lookback_period=20
    )
```

### Project and Backtest Management

```python
# Create new algorithmic trading project
project = await create_project(
    name="Mean_Reversion_Strategy_v2",
    language="Py"
)

# Upload algorithm code
await create_file(
    project_id=project["project"]["projectId"],
    name="main.py",
    content=algorithm_code
)

# Run backtest
backtest = await create_backtest(
    project_id=project["project"]["projectId"],
    compile_id="latest",
    backtest_name="Mean_Reversion_Test_Run",
    parameters={"lookback_period": 20, "threshold": 2.0}
)

# Analyze results
results = await read_backtest(
    project_id=project["project"]["projectId"],
    backtest_id=backtest["backtest"]["backtestId"]
)
```

## ◈ Comprehensive API Reference

### ◆ Authentication Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `configure_quantconnect_auth` | Set up API credentials | `user_id`, `api_token`, `organization_id` |
| `validate_quantconnect_auth` | Test credential validity | - |
| `get_auth_status` | Check authentication status | - |
| `test_quantconnect_api` | Test API connectivity | `endpoint`, `method` |
| `clear_quantconnect_auth` | Clear stored credentials | - |

### ◆ Project Management Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `create_project` | Create new QuantConnect project | `name`, `language`, `organization_id` |
| `read_project` | Get project details or list all | `project_id` (optional) |
| `update_project` | Update project name/description | `project_id`, `name`, `description` |

### ◆ File Management Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `create_file` | Create file in project | `project_id`, `name`, `content` |
| `read_file` | Read file(s) from project | `project_id`, `name` (optional) |
| `update_file_content` | Update file content | `project_id`, `name`, `content` |
| `update_file_name` | Rename file in project | `project_id`, `old_file_name`, `new_name` |

### ◆ QuantBook Research Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `initialize_quantbook` | Create new research instance | `instance_name`, `organization_id`, `token` |
| `list_quantbook_instances` | View all active instances | - |
| `get_quantbook_info` | Get instance details | `instance_name` |
| `remove_quantbook_instance` | Clean up instance | `instance_name` |

### ◆ Data Retrieval Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `add_equity` | Add single equity security | `ticker`, `resolution`, `instance_name` |
| `add_multiple_equities` | Add multiple securities | `tickers`, `resolution`, `instance_name` |
| `get_history` | Get historical price data | `symbols`, `start_date`, `end_date`, `resolution` |
| `add_alternative_data` | Subscribe to alt data | `data_type`, `symbol`, `instance_name` |
| `get_alternative_data_history` | Get alt data history | `data_type`, `symbols`, `start_date`, `end_date` |

### ◆ Statistical Analysis Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `perform_pca_analysis` | Principal Component Analysis | `symbols`, `start_date`, `end_date`, `n_components` |
| `test_cointegration` | Engle-Granger cointegration test | `symbol1`, `symbol2`, `start_date`, `end_date` |
| `analyze_mean_reversion` | Mean reversion analysis | `symbols`, `start_date`, `end_date`, `lookback_period` |
| `calculate_correlation_matrix` | Asset correlation analysis | `symbols`, `start_date`, `end_date` |

### ◆ Portfolio Optimization Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `sparse_optimization` | **Advanced sparse optimization** | `portfolio_symbols`, `benchmark_symbol`, optimization params |
| `calculate_portfolio_performance` | Performance metrics | `symbols`, `weights`, `start_date`, `end_date` |
| `optimize_equal_weight_portfolio` | Equal-weight optimization | `symbols`, `start_date`, `end_date`, `rebalance_frequency` |

### ◆ Universe Selection Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `get_etf_constituents` | Get ETF holdings | `etf_ticker`, `date`, `instance_name` |
| `add_etf_universe_securities` | Add all ETF constituents | `etf_ticker`, `date`, `resolution` |
| `select_uncorrelated_assets` | Find uncorrelated assets | `symbols`, `num_assets`, `method` |
| `screen_assets_by_criteria` | Multi-criteria screening | `symbols`, `min_return`, `max_volatility`, etc. |

### ◆ Backtest Management Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `create_backtest` | Create new backtest | `project_id`, `compile_id`, `backtest_name` |
| `read_backtest` | Get backtest results | `project_id`, `backtest_id`, `chart` |
| `read_backtest_chart` | Get chart data | `project_id`, `backtest_id`, `name` |
| `read_backtest_orders` | Get order history | `project_id`, `backtest_id`, `start`, `end` |
| `read_backtest_insights` | Get insights data | `project_id`, `backtest_id`, `start`, `end` |

## ◈ Architecture

```
quantconnect-mcp/
├── ◆  quantconnect_mcp/          # Main package directory
│   ├── main.py                   # Server entry point & configuration
│   └── src/                      # Source code modules
│       ├── ⚙  server.py          # FastMCP server core
│       ├── ⚙  tools/             # Tool implementations
│       │   ├── ▪  auth_tools.py      # Authentication management
│       │   ├── ▪  project_tools.py   # Project CRUD operations
│       │   ├── ▪  file_tools.py      # File management
│       │   ├── ▪  quantbook_tools.py # Research environment
│       │   ├── ▪  data_tools.py      # Data retrieval
│       │   ├── ▪  analysis_tools.py  # Statistical analysis
│       │   ├── ▪  portfolio_tools.py # Portfolio optimization
│       │   ├── ▪  universe_tools.py  # Universe selection
│       │   └── ▪  backtest_tools.py  # Backtest management
│       ├── ◆  auth/              # Authentication system
│       │   ├── __init__.py
│       │   └── quantconnect_auth.py   # Secure API authentication
│       └── ◆  resources/         # System resources
│           ├── __init__.py
│           └── system_resources.py   # Server monitoring
├── ◆  tests/                     # Comprehensive test suite
│   ├── test_auth.py
│   ├── test_server.py
│   └── __init__.py
├── ◆  pyproject.toml             # Project configuration
└── ◆  README.md                  # This file
```

### Core Design Principles

- **◎ Modular Architecture**: Each tool category is cleanly separated for maintainability
- **▪ Security First**: SHA-256 authenticated API with secure credential management  
- **⚡ Async Performance**: Non-blocking operations for maximum throughput
- **◆ Type Safety**: Full type annotations with mypy verification
- **⚙ Extensible**: Plugin-based architecture for easy feature additions

## ◈ Advanced Configuration

### Transport Options

```bash
# STDIO (default) - Best for MCP clients
uvx quantconnect-mcp

# HTTP Server - Best for web integrations
MCP_TRANSPORT=streamable-http MCP_HOST=0.0.0.0 MCP_PORT=8000 uvx quantconnect-mcp

# Custom path for HTTP
MCP_PATH=/api/v1/mcp uvx quantconnect-mcp

# Development mode with local changes
uv run quantconnect_mcp/main.py
```

### Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `MCP_TRANSPORT` | Transport method | `stdio` | `streamable-http` |
| `MCP_HOST` | Server host | `127.0.0.1` | `0.0.0.0` |
| `MCP_PORT` | Server port | `8000` | `3000` |
| `MCP_PATH` | HTTP endpoint path | `/mcp` | `/api/v1/mcp` |
| `LOG_LEVEL` | Logging verbosity | `INFO` | `DEBUG` |

### System Resources

Monitor server performance and status:

```python
# System information
system_info = await get_resource("resource://system/info")

# Server status and active instances  
server_status = await get_resource("resource://quantconnect/server/status")

# Available tools summary
tools_summary = await get_resource("resource://quantconnect/tools/summary")

# Performance metrics
performance = await get_resource("resource://quantconnect/performance/metrics")

# Top processes by CPU usage
top_processes = await get_resource("resource://system/processes/10")
```

## ◈ Testing

### Run the Test Suite

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test category
pytest tests/test_auth.py -v

# Run tests in parallel
pytest tests/ -n auto
```

### Manual Testing

```bash
# Test authentication
python -c "
import asyncio
from src.auth import validate_authentication
print(asyncio.run(validate_authentication()))
"

# Test server startup
uvx quantconnect-mcp --help
```

## ◈ Contributing

We welcome contributions! This project follows the highest Python development standards:

### Development Setup

```bash
# Fork and clone the repository
git clone https://github.com/your-username/quantconnect-mcp
cd quantconnect-mcp

# Install development dependencies
uv sync --dev

# Install pre-commit hooks
pre-commit install
```

### Code Quality Standards

- ◉ **Type Hints**: All functions must have complete type annotations
- ◉ **Documentation**: Comprehensive docstrings for all public functions
- ◉ **Testing**: Minimum 90% test coverage required
- ◉ **Formatting**: Black code formatting enforced
- ◉ **Linting**: Ruff linting with zero warnings
- ◉ **Type Checking**: mypy verification required

### Development Workflow

```bash
# Create feature branch
git checkout -b feature/amazing-new-feature

# Make changes and run quality checks
ruff check src/
black src/ tests/
mypy src/

# Run tests
pytest tests/ --cov=src

# Commit with conventional commits
git commit -m "feat: add amazing new feature"

# Push and create pull request
git push origin feature/amazing-new-feature
```

### Pull Request Guidelines

1. **◆ Clear Description**: Explain what and why, not just how
2. **◆ Test Coverage**: Include tests for all new functionality  
3. **◆ Documentation**: Update README and docstrings as needed
4. **◆ Code Review**: Address all review feedback
5. **◆ CI Passing**: All automated checks must pass

## ◈ License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with precision for the algorithmic trading community**

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://python.org)
[![FastMCP](https://img.shields.io/badge/FastMCP-v2.7%2B-green.svg)](https://github.com/fastmcp/fastmcp)
[![QuantConnect](https://img.shields.io/badge/QuantConnect-API%20v2-orange.svg)](https://www.quantconnect.com)

[◉ Star this repo](https://github.com/your-org/quantconnect-mcp) •
[◉ Report issues](https://github.com/your-org/quantconnect-mcp/issues) •
[◉ Request features](https://github.com/your-org/quantconnect-mcp/discussions)

</div>