# dot-configs-ai

A personal collection of AI skills I use.. 

## Skills

| Skill | What it does |
|-------|-------------|
| **memory** | Remembers your preferences, past mistakes, and project context across conversations so you stop repeating yourself. |
| **code-review** | Reviews staged code before you commit — catches dead code, DRY violations, missing docs, and linter.. |
| **plantuml-generator** | Turns `.puml` files into PNGs locally, and can extract the source back out of a generated image. |
| **mcp-builder** | A guide for building MCP servers.. upsteam is claude mcp builder skill |
| **skill-creator** | upstream is claude skill creator |
| **ipynb-editor** | Edit `.ipynb` Jupyter notebook files directly safely using find and replace. |
| **searxng** | Self-hosted private web search via a local SearXNG metasearch engine — no tracking, no rate limits. |

## MCP Servers

| Server | What it does |
|--------|-------------|
| **searxng** | Self-managing, self-contained MCP server for private web search. — no Docker, ~60MB memory usage |

### Setup

```bash
# 1. Create venv and install MCP dependencies (one-time)
cd mcp/searxng
python3 -m venv .venv

# 2. Register in Claude Code settings.json
# Add to the "mcpServers" block:
{
  "mcpServers": {
    "searxng": {
      "command": "/path/to/mcp/searxng/.venv/bin/python3",
      "args": ["/path/to/mcp/searxng/server.py"]
    }
  }
}
```

First launch downloads and installs SearXNG (~60s). Subsequent launches are instant.

### Tests

```bash
cd mcp/searxng
.venv/bin/python3 test_server.py
```

## Structure

```
mcp/
└── searxng/           # SearXNG MCP server (self-contained)

skills/
├── memory/            
├── code-review/       
├── plantuml-generator/ 
├── mcp-builder/       
├── skill-creator/     
├── ipynb-editor/
└── searxng/
```

## Usage

Drop the `skills/` folder (or individual skills) into your project or global config. Any AI agent that supports skill loading will pick them up automatically.
