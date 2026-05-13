# 🤖 Percival Khan Calendar - percival.OS MCP

**Version 0.0.2**

[![Python](https://img.shields.io/badge/python-3.10+-yellow.svg)]()
[![MCP](https://img.shields.io/badge/mcp-server-blue.svg)]()
[![percival.OS](https://img.shields.io/badge/percival.OS-ecosystem-orange.svg)](https://github.com/bill-kopp-ai-dev/percival.OS)

## 📋 Description
**Percival Khan Calendar** is an MCP server that provides the Nanobot agent with autonomous, persistent, and secure capabilities to manage a local calendar using the `khal` library.

This server is part of the **percival.OS** ecosystem, a Personal Agentic Operating System designed for autonomy, security, and absolute privacy.

---

## 🛡️ percival.OS Principles
Like all components of `percival.OS`, this MCP server strictly follows our core principles:

- **Local-First & Private**: Operates entirely on the local filesystem. Your appointments are never sent to the cloud without your explicit consent.
- **Data Sovereignty**: The calendar is stored in your infrastructure, ensuring your schedule remains private.
- **Hardened Security**: We implement "Prompt Injection Shields" by wrapping calendar data in XML tags and providing explicit instructions to the LLM to prevent indirect manipulation.
- **Transparency**: Open-source and auditable to ensure full governance of your data.

---

## 🚀 Features & Tools
The server offers complete CRUD and visualization tools:

- `khan_list_events`: List scheduled events for a specific day or period.
- `khan_search_events`: Full-text search across the entire calendar database.
- `khan_create_event`: Create new appointments with support for alarms and recurrence.
- `khan_update_event`: Atomically update existing events.
- `khan_delete_event`: Permanently remove a specific event.
- `khan_view_agenda`: Optimized agenda list for mobile/Telegram displays.
- `khan_view_calendar`: Visual ASCII matrix of the month.
- `khan_get_status`: Check operational status of the calendar server.

---

## ⚙️ Configuration in percival.OS (Nanobot)
Add the following configuration to your `~/.nanobot/config.json`:

```json
{
  "tools": {
    "mcpServers": {
      "percival-khan-calendar": {
        "command": "uv",
        "args": [
          "run",
          "--directory",
          "/home/bill-kopp/Documents/percival.OS/percival.OS_Dev/mcp_servers/percival-khan-calendar",
          "python",
          "-m",
          "percival_khan_calendar.server"
        ],
        "env": {
          "UV_PROJECT_ENVIRONMENT": "/home/bill-kopp/Documents/percival.OS/percival.OS_Dev/.venv",
          "PYTHONPATH": "/home/bill-kopp/Documents/percival.OS/percival.OS_Dev/mcp_servers/percival-khan-calendar/src"
        },
        "toolTimeout": 60
      }
    }
  }
}
```

---

## 🛠️ Development & Testing
This project uses `uv` for dependency management.

```bash
# Sync environment
uv sync

# Run tests (if available)
uv run pytest
```

---

## 📚 About the Project
This server is an integral module of the **percival.OS** project. It acts as an agentic wrapper for `khal`, allowing Nanobot to manage your schedule intelligently.

- **Main Repository**: [https://github.com/bill-kopp-ai-dev/percival.OS](https://github.com/bill-kopp-ai-dev/percival.OS)
- **License**: MIT

---
*Developed with ❤️ by the percival.OS Team*
