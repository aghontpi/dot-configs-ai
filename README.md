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

## Structure

```
skills/
├── memory/            
├── code-review/       
├── plantuml-generator/ 
├── mcp-builder/       
├── skill-creator/     
└── ipynb-editor/
```

## Usage

Drop the `skills/` folder (or individual skills) into your project or global config. Any AI agent that supports skill loading will pick them up automatically.
