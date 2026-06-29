# 🕒 MCP Time Server ⚡

A Model Context Protocol (MCP) server providing comprehensive time utilities to AI clients like Claude Desktop and Cursor. Built with Python using the FastMCP framework.

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   AI Client     │◄──►│   MCP Server     │◄──►│  Time Services  │
│ (Claude/Cursor) │    │   (timeserver)   │    │   (Python)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Setup & Installation
```bash
cd /Users/joshpriebe/Documents/AI/mcp/timeserver
source .venv/bin/activate
python test_timeserver.py  # Verify everything works
```

### Project Structure
```
timeserver/
├── main.py                     # 🔧 MCP server implementation
├── test_timeserver.py         # 🧪 Comprehensive tests  
├── pyproject.toml             # 📦 Python dependencies
├── claude_desktop_config.json # ⚙️  Claude config
├── cursor_global_mcp.json     # ⚙️  Cursor config template
└── .cursor/mcp.json           # ⚙️  Project Cursor config
```

## 🛠️ Available Tools

```lua
┌─────────────────────────────────────────────────────────────┐
│                    Time Server Tools                        │
├─────────────────────────────────────────────────────────────┤
│  🌍 get_current_time(timezone="UTC")                        │
│      Get current time in any timezone                       │
│                                                             │
│  🌐 get_time_in_multiple_zones()                            │
│      World clock across 10 major timezones                  │
│                                                             │
│  📊 get_unix_timestamp()                                    │
│      Current Unix timestamp + readable format               │
│                                                             │
│  🔄 format_time(timestamp)                                  │
│      Convert Unix timestamp to human-readable               │
└─────────────────────────────────────────────────────────────┘
```

## 🔌 Client Integration

### Claude Desktop
Configuration file: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "timeserver": {
      "command": "/Users/joshpriebe/Documents/AI/mcp/timeserver/.venv/bin/python",
      "args": ["/Users/joshpriebe/Documents/AI/mcp/timeserver/main.py"],
      "env": {
        "PYTHONPATH": "/Users/joshpriebe/Documents/AI/mcp/timeserver",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

### Cursor
**Project config** (already configured): `.cursor/mcp.json`
**Global config**: Copy `cursor_global_mcp.json` to `~/.cursor/mcp.json`

## 💡 Example Usage

### Natural Language Queries
```
🕐 Basic Time
├── "What time is it?"
├── "Current time please"
└── "What's the time right now?"

🌍 Timezone Queries  
├── "What time is it in London?"
├── "Show me Tokyo time"
└── "Current time in US/Pacific"

🌐 World Clock
├── "Show me world clock"
├── "Time in multiple cities" 
└── "What time is it around the world?"

📊 Unix Timestamps
├── "Current timestamp"
├── "Give me the epoch time"
└── "Convert 1704067200 to date"
```

### API Examples
```python
# Get current time in specific timezone
await get_current_time("US/Pacific")
# → "Current time in US/Pacific: 2024-01-01 04:00:00 PST"

# Get world clock
await get_time_in_multiple_zones()
# → Multi-line output with 10 timezones

# Get Unix timestamp
await get_unix_timestamp() 
# → "Current Unix timestamp: 1704067200\nHuman readable (UTC): ..."

# Convert timestamp
await format_time(1704067200)
# → "Timestamp 1704067200 converts to:\nLocal time: ...\nUTC time: ..."
```

## 🧪 Testing

```bash
# Test all functionality
python test_timeserver.py

# Test MCP protocol communication  
python test_mcp_protocol.py
```

**Test Flow:**
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Unit      │───►│    MCP      │───►│   Manual    │
│   Tests     │    │  Protocol   │    │   Testing   │
│             │    │   Tests     │    │ (AI Client) │
└─────────────┘    └─────────────┘    └─────────────┘
```

## 🔍 Troubleshooting

### Quick Diagnostics
```bash
# 1. Verify Python environment
ls -la .venv/bin/python

# 2. Test server directly  
python main.py

# 3. Check configuration
cat .cursor/mcp.json  # or
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### Common Issues
```
❌ "No tools available" 
   → Restart AI client after config changes
   
❌ "Server not responding"
   → Check Python path in configuration
   
❌ "Import errors"  
   → Activate virtual environment: source .venv/bin/activate
```

## 🔧 Development

### Dependencies
```bash
# Runtime
pip install "mcp[cli]>=1.0.0"

# Development (optional)
pip install black isort pylint mypy pytest pytest-asyncio
```

### Code Quality
```bash
black main.py test_timeserver.py    # Format
isort main.py test_timeserver.py    # Sort imports  
pylint main.py                      # Lint
mypy main.py                        # Type check
```

## 📜 License

MIT License - Open source time utilities for the MCP ecosystem.

---

**🕐 Happy time tracking!** Your MCP Time Server provides accurate time information across any AI client supporting the Model Context Protocol.
