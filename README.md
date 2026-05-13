# Percival Khan Calendar MCP Server

A Model Context Protocol (MCP) server that provides the **Nanobot** agent (or any other MCP-compatible assistant) with autonomous, persistent, and secure capabilities to manage a local calendar using the `khal` library.

This module is a core component of the [percival.OS ecosystem](https://github.com/bill-kopp-ai-dev/percival.OS), explicitly designed for agentic workflows where privacy and local data sovereignty are paramount.

> [!IMPORTANT]
> This server acts as an agentic wrapper for `khal`. It bypasses CLI interactive constraints (ncurses) by directly manipulating `.ics` files via the `icalendar` library for update/delete operations, ensuring atomic and deterministic state management.

## Features

- **Local-First & Private**: Operates entirely on the local filesystem. No cloud APIs or external sync required (unless configured via `vdirsyncer` independently).
- **Agentic CRUD**: Full support for creating, reading, searching, updating, and deleting events.
- **Rich UI Rendering**: Optimized output for chat interfaces (like Telegram) with ASCII monthly grids and chronological agenda lists.
- **Cognitive Security**: Implements "Prompt Injection Shields" by wrapping untrusted calendar data in XML tags and providing explicit instructions to the LLM.
- **Robust Execution**: Uses a custom subprocess wrapper to capture CLI errors and translate them into actionable natural language for the agent.

## Tools Included

- `list_events`: List scheduled events for a specific day or period.
- `search_events`: Full-text search across the entire calendar database.
- `create_event`: Create new appointments with support for alarms and recurrence.
- `update_event`: Atomically update existing events (Delete & Recreate pattern).
- `delete_event`: Permanently remove a specific event from the database.
- `view_agenda_list`: Optimized list view for mobile/Telegram displays.
- `view_calendar_grid`: Visual ASCII matrix of the month.

## Installation

This project uses `uv` for dependency management.

1. Ensure you have `uv` installed:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Clone and sync:
   ```bash
   cd percival.OS/percival.OS_Dev/mcp_servers/percival-khan-calendar
   uv sync
   ```

## Configuration

The server automatically initializes its own workspace and configuration in `~/.nanobot/workspace/khalCalendar/`.

### Integrating with Nanobot

Add the following block to your Nanobot `config.json`:

```json
{
  "mcpServers": {
    "percival-khan-calendar": {
      "command": "uv",
      "args": [
        "run",
        "--no-sync",
        "--directory",
        "/home/bill-kopp/Documents/percival.OS/percival.OS_Dev/mcp_servers/percival-khan-calendar",
        "python",
        "-m",
        "percival_khan_calendar.server"
      ],
      "env": {
        "UV_PROJECT_ENVIRONMENT": "/home/bill-kopp/Documents/percival.OS/percival.OS_Dev/.venv",
        "PYTHONPATH": "/home/bill-kopp/Documents/percival.OS/percival.OS_Dev/mcp_servers/percival-khan-calendar/src",
        "PYTHONUNBUFFERED": "1"
      },
      "toolTimeout": 60
    }
  }
}
```

## Project Structure

```
.
├── pyproject.toml              # Independent project config
├── README.md                   # This file
└── src/
    └── percival_khan_calendar/ # Source code
        ├── __init__.py
        └── server.py           # FastMCP implementation & logic
```

## Security & Guardrails

- **Prompt Injection Shield**: All event descriptions are treated as untrusted data. The server wraps these in `<calendar_untrusted_data>` tags to prevent indirect prompt injections.
- **Output Truncation**: All visual tools truncate output at 4,000 characters to prevent context window overflows and Telegram message limits.
- **Isolated Workspace**: Uses a dedicated `khal.conf` generated at runtime to prevent interference with the host system's global calendar settings.

## License

This project is licensed under the MIT License.
