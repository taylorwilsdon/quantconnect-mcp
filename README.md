<div align="center">

# ◆ QuantConnect MCP Server

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://python.org)
[![FastMCP](https://img.shields.io/badge/FastMCP-v2.7%2B-green.svg)](https://github.com/fastmcp/fastmcp)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/Code%20Style-Black-black.svg)](https://github.com/psf/black)
[![Type Checked](https://img.shields.io/badge/Type%20Checked-mypy-blue.svg)](https://mypy.readthedocs.io/)

**Production-ready Model Context Protocol server for QuantConnect's algorithmic trading platform**

*Integrate QuantConnect's research environment, statistical analysis, and portfolio optimization into your AI workflows. Locally hosted, secure & capable of dramatically improving productivity*

[◉ Quick Start](#-quick-start) •
[◉ Documentation](#-comprehensive-api-reference) •
[◉ Architecture](#-architecture) •
[◉ Contributing](#-contributing)

</div>

<details open>
<summary>Demo – Claude</summary>

<div align="center">
  <video width="832" src="https://github.com/user-attachments/assets/61e96e0e-05b2-482b-8fe3-ccf078d64cc5"></video>
</div>

</details>


---

## ◈ Is this crazy?
<div align="center">
<img width="25%" height="25%" alt="image" src="https://github.com/user-attachments/assets/f282cb1e-7fde-4efd-b28c-2656c9f48fea" />
</div>
Maybe? Either way, the world is changing and this is where we're at.
Out of the box, QuantConnect MCP provides you with:

- **Full Project Lifecycle**: `Create`, `read`, `update`, `compile`, and manage QuantConnect projects and files programmatically.
- **End-to-End Backtesting**: `Compile` projects, `create backtests`, `read detailed results`, and analyze `charts`, `orders`, and `insights`.
- **Interactive Research**: Full `QuantBook` integration for dynamic financial analysis, including historical and `alternative data` retrieval.
- **Advanced Analytics**: Perform `Principal Component Analysis (PCA)`, `Engle-Granger cointegration tests`, `mean-reversion analysis`, and `correlation studies`.
- **Portfolio Optimization**: Utilize sophisticated `sparse optimization` with Huber Downward Risk minimization, calculate performance, and benchmark strategies.
- **Universe Selection**: Dynamically `screen assets` by multiple criteria, analyze `ETF constituents`, and select assets based on correlation.
- **Enterprise-Grade Security**: Secure, `SHA-256 authenticated` API integration with QuantConnect.
- **High-Performance Core**: Built with an `async-first` design for concurrent data processing and responsiveness.
- **AI-Native Interface**: Designed for seamless interaction via `natural language` in advanced AI clients.

## ◉ Table of Contents

- [◈ Quick Start](#-quick-start)
- [◈ Authentication](#-authentication)
- [◈ Natural Language Examples](#-natural-language-examples)
- [◈ Comprehensive API Reference](#-comprehensive-api-reference)
- [◈ Architecture](#-architecture)
- [◈ Advanced Configuration](#-advanced-configuration)
- [◈ Testing](#-testing)
- [◈ Contributing](#-contributing)
- [◈ License](#-license)

## ◈ Quick Start

Get up and running in under 2 minutes:

> **Prerequisites:** You must have QuantConnect credentials (User ID and API Token) before running the server. The server will not function without proper authentication. See [Authentication](#-authentication) section for details on obtaining these credentials.

### **Install with uvx (Recommended)**

#### Core Installation (API Tools Only)
```bash
# Install and run directly from PyPI - no cloning required!
uvx quantconnect-mcp

# Or install with uv/pip
uv pip install quantconnect-mcp
pip install quantconnect-mcp
```

#### Full Installation (with QuantBook Support)
```bash
# Install with QuantBook container functionality
uv pip install "quantconnect-mcp[quantbook]"
pip install "quantconnect-mcp[quantbook]"

# Requires Docker to be installed and running
docker --version  # Ensure Docker is available
```


### One-Click Claude Desktop Install (Recommended)

1. **Download:** Grab the latest `quantconnect-mcp.dxt` from the “Releases” page
2. **Install:** Double-click the file – Claude Desktop opens and prompts you to **Install**
3. **Configure:** In Claude Desktop → **Settings → Extensions → QuantConnect MCP**, paste your user ID and API token
4. **Use it:** Start a new Claude chat and call any QuantConnect tool


**Why DXT?**
> Desktop Extensions (`.dxt`) bundle the server, dependencies, and manifest so users go from download → working MCP in **one click** – no terminal, no JSON editing, no version conflicts.

### 2. **Set Up QuantConnect Credentials (Required)**
**The server requires these environment variables to function properly:**
```bash
export QUANTCONNECT_USER_ID="your_user_id"        # Required
export QUANTCONNECT_API_TOKEN="your_api_token"    # Required
export QUANTCONNECT_ORGANIZATION_ID="your_org_id" # Optional

# Optional: Enable QuantBook container functionality (default: false)
export ENABLE_QUANTBOOK="true"                    # Requires Docker + quantconnect-mcp[quantbook]
```

### 3. **Launch the Server**
```bash
# STDIO transport (default) - Recommended for MCP clients
uvx quantconnect-mcp

# With QuantBook functionality enabled
ENABLE_QUANTBOOK=true uvx quantconnect-mcp

# HTTP transport
MCP_TRANSPORT=streamable-http MCP_PORT=8000 uvx quantconnect-mcp

# Full configuration example
ENABLE_QUANTBOOK=true \
LOG_LEVEL=DEBUG \
MCP_TRANSPORT=streamable-http \
MCP_PORT=8000 \
uvx quantconnect-mcp
```

### 4. **QuantBook Container Functionality (Optional)**

The server supports optional QuantBook functionality that runs research environments in secure Docker containers. This provides:

- **🐳 Containerized Execution**: Each QuantBook instance runs in an isolated Docker container
- **🔒 Enhanced Security**: Non-root users, capability dropping, resource limits
- **⚡ Scalable Sessions**: Multiple concurrent research sessions with automatic cleanup
- **📊 Interactive Analysis**: Execute Python code with full QuantConnect research libraries

#### **Requirements**
- Docker installed and running
- Install with QuantBook support: `pip install "quantconnect-mcp[quantbook]"`
- Set environment variable: `ENABLE_QUANTBOOK=true`

#### **Security Features**
- Containers run as non-root users (1000:1000)
- Network isolation (no external network access)
- Resource limits (configurable memory and CPU)
- Automatic session timeout and cleanup
- Code execution monitoring and logging

#### **Container Configuration**
```bash
# Container resource limits (optional)
export QUANTBOOK_MEMORY_LIMIT="2g"      # Default: 2GB RAM
export QUANTBOOK_CPU_LIMIT="1.0"        # Default: 1 CPU core
export QUANTBOOK_SESSION_TIMEOUT="3600" # Default: 1 hour timeout
```

### 5. **Interact with Natural Language**

Instead of calling tools programmatically, you use natural language with a connected AI client (like Claude, a GPT, or any other MCP-compatible interface).

> "Initialize a research environment, add GOOGL, AMZN, and MSFT, then run a PCA analysis on them for 2023."


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

<details open>
<summary>Demo – Roo Code</summary>

<div align="center">
  <video width="832" src="https://github.com/user-attachments/assets/4d0e8074-aa27-4041-befc-b4119b5eaec6"></video>
</div>

</details>

## ◈ Natural Language Examples

This MCP server is designed to be used with natural language. Below are examples of how you can instruct an AI assistant to perform complex financial analysis tasks.

### Factor‑Driven Portfolio Construction Pipeline

> **“Build a global equity long/short portfolio for 2025:**
> 1. Pull the **constituents of QQQ, SPY, and EEM** as of **2024‑12‑31** (survivor‑bias free).
> 2. For each symbol, calculate **Fama‑French 5‑factor** and **quality‑minus‑junk** loadings using daily data **2022‑01‑01 → 2024‑12‑31**.
> 3. Rank stocks into terciles on **value (B/M)** and **momentum (12‑1)**; go long top tercile, short bottom, beta‑neutral to the S&P 500.
> 4. Within each book, apply **Hierarchical Risk Parity (HRP)** for position sizing, capped at **5 % gross exposure per leg**.
> 5. Target **annualised ex‑ante volatility ≤ 10 %**; solve with **CVaR minimisation** under a 95 % confidence level.
> 6. Benchmark against **MSCI World**; report **annualised return, vol, Sharpe, Sortino, max DD, hit‑rate, turnover** for the period **2023‑01‑01 → 2024‑12‑31**.
> 7. Export the optimal weights and full tear‑sheet as `pdf` + `csv`.
> 8. Schedule a monthly rebalance job and push signals to the live trading endpoint.”

---

### Robust Statistical‑Arbitrage Workflow

> **“Test and refine a pairs‑trading idea:**
> • Universe: **US Staples sector, market cap > $5 B, price > $10**.
> • Data: **15‑minute bars, 2023‑01‑02 → 2025‑06‑30**.
> • Step 1 – For all pairs, calculate **rolling 60‑day distance correlation**; keep pairs with dCor ≥ 0.80.
> • Step 2 – Run **Johansen cointegration** (lag = 2) on the survivors; retain pairs with trace‑stat < 5 % critical value.
> • Step 3 – For each cointegrated pair:
>    – Estimate **half‑life of mean‑reversion**; discard if > 7 days.
>    – Compute **Hurst exponent**; require H < 0.4.
> • Step 4 – Simulate a **Bayesian Kalman‑filter spread** to allow time‑varying hedge ratios.
> • Entry: z‑score crosses ±2 (two‑bar confirmation); Exit: z = 0 or t_max = 3 × half‑life.
> • Risk: cap **pair notional at 3 % NAV**, portfolio **gross leverage ≤ 3 ×**, stop‑loss at z = 4.
> • Output: trade log, PnL attribution, **bootstrapped p‑value of alpha**, and **Likelihood‑Ratio test** for regime shifts.”


### Automated Project, Backtest & Hyper‑Parameter Sweep

> **“Spin up an experiment suite in QuantConnect:**
> 1. Create project **‘DynamicPairs_Kalman’** (Python).
> 2. Add files:
>    • `alpha.py` – signal generation (placeholder)
>    • `risk.py` – custom position sizing
>    • `config.yaml` – parameter grid:
>        ```yaml
>        entry_z:  [1.5, 2.0, 2.5]
>        lookback: [30, 60, 90]
>        hedge:    ['OLS', 'Kalman']
>        ```
> 3. Trigger a **parameter‑sweep backtest** labelled **‘GridSearch‑v1’** using **in‑sample 2022‑23**.
> 4. When jobs finish, rank runs by **Information Ratio** and **max DD < 10 %**; persist **top‑3 configs**.
> 5. Automatically launch **out‑of‑sample backtests 2024‑YTD** for the winners.
> 6. Produce an executive summary: tables + charts (equity curve, rolling Sharpe, exposure histogram).
> 7. Package the best model as a **Docker image**, push to registry, and deploy to the **live‑trading cluster** with a kill‑switch if **1‑day loss > 3 σ**.”

### Statistical Analysis Workflow

> "Are Coca-Cola (KO) and Pepsi (PEP) cointegrated? Run the test for the period from 2023 to 2024. If they are, analyze their mean-reversion properties with a 20-day lookback."

### Project and Backtest Management

> "I need to manage my QuantConnect projects. First, create a new Python project named 'My_Awesome_Strategy'. Then, create a file inside it called 'main.py' and add this code: `...your algorithm code here...`. After that, compile it and run a backtest named 'Initial Run'. When it's done, show me the performance results."

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
| `compile_project` | Compile a project for backtesting | `project_id` |

### ◆ File Management Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `create_file` | Create file in project | `project_id`, `name`, `content` |
| `read_file` | Read file(s) from project | `project_id`, `name` (optional) |
| `update_file_content` | Update file content | `project_id`, `name`, `content` |
| `update_file_name` | Rename file in project | `project_id`, `old_file_name`, `new_name` |

### ◆ QuantBook Research Tools (Optional - Requires ENABLE_QUANTBOOK=true)

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `initialize_quantbook` | Create new containerized research instance | `instance_name`, `memory_limit`, `cpu_limit`, `timeout` |
| `list_quantbook_instances` | View all active container instances | - |
| `get_quantbook_info` | Get container instance details | `instance_name` |
| `remove_quantbook_instance` | Clean up container instance | `instance_name` |
| `execute_quantbook_code` | Execute Python code in container | `code`, `instance_name`, `timeout` |
| `get_session_manager_status` | Get container session manager status | - |

### ◆ Data Retrieval Tools (Optional - Requires ENABLE_QUANTBOOK=true)

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `add_equity` | Add single equity security to container | `ticker`, `resolution`, `instance_name` |
| `add_multiple_equities` | Add multiple securities to container | `tickers`, `resolution`, `instance_name` |
| `get_history` | Get historical price data in container | `symbols`, `start_date`, `end_date`, `resolution` |
| `add_alternative_data` | Subscribe to alt data in container | `data_type`, `symbol`, `instance_name` |
| `get_alternative_data_history` | Get alt data history in container | `data_type`, `symbols`, `start_date`, `end_date` |

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
| `create_backtest` | Create new backtest from compile | `project_id`, `compile_id`, `backtest_name` |
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

### Environment Variables

#### Core Server Configuration
| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `MCP_TRANSPORT` | Transport method | `stdio` | `streamable-http` |
| `MCP_HOST` | Server host | `127.0.0.1` | `0.0.0.0` |
| `MCP_PORT` | Server port | `8000` | `3000` |
| `MCP_PATH` | HTTP endpoint path | `/mcp` | `/api/v1/mcp` |
| `LOG_LEVEL` | Logging verbosity | `INFO` | `DEBUG` |
| `LOG_FILE` | Log file path | None | `/var/log/quantconnect-mcp.log` |

#### QuantConnect Authentication
| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `QUANTCONNECT_USER_ID` | Your QuantConnect user ID | ◉ Yes | `123456` |
| `QUANTCONNECT_API_TOKEN` | Your QuantConnect API token | ◉ Yes | `abc123...` |
| `QUANTCONNECT_ORGANIZATION_ID` | Organization ID (optional) | ◦ No | `org123` |

#### QuantBook Container Configuration (Optional)
| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `ENABLE_QUANTBOOK` | Enable QuantBook functionality | `false` | `true` |
| `QUANTBOOK_MEMORY_LIMIT` | Container memory limit | `2g` | `4g` |
| `QUANTBOOK_CPU_LIMIT` | Container CPU limit | `1.0` | `2.0` |
| `QUANTBOOK_SESSION_TIMEOUT` | Session timeout (seconds) | `3600` | `7200` |
| `QUANTBOOK_MAX_SESSIONS` | Maximum concurrent sessions | `10` | `20` |

### System Resources

You can monitor server performance and status using natural language queries for system resources:

> "Show me the server's system info."

> "What's the current server status and are there any active QuantBook instances?"

> "Give me a summary of all available tools."

> "Get the latest performance metrics for the server."

> "What are the top 10 most resource-intensive processes running on the server?"

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
