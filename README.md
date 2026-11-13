# Percival Khan Calendar

Docker-first, stdio MCP server for managing a local calendar with [`khal`](https://github.com/pimutils/khal).
The server exposes 12 tools, 6 prompts and the `khan://schema/main` reference resource.

Calendar data stays in a local workspace mounted into the container. The server does not expose a network port; an MCP client communicates with it over stdin/stdout.

## Features

- Read, search, view, create, update and delete calendar events; safely preview deletions and export ICS.
- Create timed or all-day events, with recurrence, location, description and alarms.
- Preserve event UID, recurrence rules and VALARM subcomponents on updates.
- Protect concurrent writes with a workspace lock enabled by default.
- Run as a non-root user (UID/GID `1000:1000`) with a read-only container root, dropped Linux capabilities and no exposed ports.
- Include `khal` and all runtime dependencies in the image; no host `khal` executable or source-code bind mount is required.

## MCP surface

### Tools

| Tool | Purpose |
|---|---|
| `khan_list_events` | List events in a date window. |
| `khan_search_events` | Search event text. |
| `khan_get_event` | Inspect one event and its details. |
| `khan_view_agenda` | Render a concise agenda. |
| `khan_view_calendar` | Render a text month calendar. |
| `khan_list_calendars` | List configured calendars. |
| `khan_get_status` | Report workspace and `khal.conf` status. |
| `khan_create_event` | Create a timed or all-day event. |
| `khan_update_event` | Update an event while preserving its UID and supported components. |
| `khan_delete_event` | Delete an event by a specific match. |
| `khan_delete_event_safe` | Preview a match, then delete only after confirmation. |
| `khan_export_ics` | Export calendar events to an ICS file. |

`khan_create_event` accepts a date-only start for an all-day event. Its `end` may be an explicit date/time or a positive elapsed duration such as `30m`, `2h`, `1d` (24 hours) or `45s`; when omitted, it defaults to one hour. `khan_export_ics` anchors relative output paths inside the configured workspace and rejects paths escaping it.

### Prompts and resource

The six prompts are `khan_overview`, `khan_create_event_semantics`, `khan_update_workflow`, `khan_delete_with_confirmation`, `khan_search_strategy` and `khan_quick_action_quick_create`. The `khan://schema/main` Markdown resource provides on-demand technical reference.

## Run with Docker

### Build and smoke-test

Requires Docker Engine with BuildKit support and Python 3.11+ for the metadata command below. `VERSION` must match `pyproject.toml`; `GIT_SHA` must be a 7–40 character lowercase commit hash (optionally suffixed `-dirty`), or `local` for a development build.

```bash
VERSION=$(python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')
GIT_SHA=$(git rev-parse --short HEAD)
test -z "$(git status --porcelain)" || GIT_SHA="${GIT_SHA}-dirty"
docker build --build-arg VERSION="$VERSION" --build-arg GIT_SHA="$GIT_SHA" \
  -t percival-khan-calendar:dev .

docker run --rm percival-khan-calendar:dev --version
```

The image runs the MCP server over stdio. Mount a persistent host workspace at `/data`; the host directory must be writable by UID/GID `1000:1000` (or have an ACL granting that access):

```bash
install -d "$HOME/.local/share/percival/khan-calendar"
sudo chown 1000:1000 "$HOME/.local/share/percival/khan-calendar"
docker run --rm -i --init --user 1000:1000 \
  -v "$HOME/.local/share/percival/khan-calendar:/data" \
  percival-khan-calendar:dev
```

The server keeps calendar state in the mounted directory across container runs. Choose a dedicated workspace and back it up according to your needs.

### Docker Compose

The included `docker-compose.yml` is a local run recipe. It builds the image, uses stdio without a TTY, enables a read-only root filesystem and mounts the persistent workspace at `/data`.

```bash
install -d "$HOME/.local/share/percival/khan-calendar"
sudo chown 1000:1000 "$HOME/.local/share/percival/khan-calendar"
docker compose build
docker compose run --rm -T server --version
docker compose run --rm -T server
```

Override the host workspace with `KHAN_CALENDAR_DATA_HOST_PATH`. Optional runtime settings can be placed in a local `.env` file based on `.env.example`; `.env` is excluded from the image build context and ignored by Git.

### Configure an MCP client

For Nanobot, add an entry to `~/.nanobot/config.json` (use absolute paths for the Compose file and workspace):

```json
{
  "tools": {
    "mcpServers": {
      "percival-khan-calendar": {
        "command": "docker",
        "args": [
          "compose", "-f", "/absolute/path/to/percival-khan-calendar/docker-compose.yml",
          "run", "--rm", "-T", "server"
        ],
        "env": {}
      }
    }
  }
}
```

Other stdio MCP clients can launch the same `docker compose ... run --rm -T server` command. Alternatively, use `docker run --rm -i` with the image and `/data` bind mount shown above. The Docker MCP Toolkit can also launch a local image through its gateway; this repository does not currently include Docker MCP Registry catalog metadata or publish an image automatically.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `KHAN_WORKSPACE_DIR` | `/data` in the container; `${XDG_DATA_HOME:-~/.local/share}/percival/khan-calendar` for source runs | Workspace containing calendar data and `khal.conf`. |
| `KHAN_TIMEZONE` | `America/Sao_Paulo` | IANA timezone used for calendar operations. |
| `KHAN_DEFAULT_CALENDAR` | `nanobot` | Default calendar name. |
| `KHAN_ENABLE_LOCK` | `true` | Lock writes; disable only when a single writer is guaranteed. |
| `KHAN_SUBPROCESS_TIMEOUT` | `15` seconds | Timeout for `khal` subprocess calls. |
| `KHAN_LOG_LEVEL` | `INFO` | Python logging level. |
| `KHAN_EXPORT_MAX_BYTES` | `16777216` | Maximum ICS export size (16 MiB). |
| `KHAN_TIMEFORMAT`, `KHAN_DATEFORMAT`, `KHAN_LONGDATEFORMAT`, `KHAN_DATETIMEFORMAT`, `KHAN_LONGDATETIMEFORMAT` | `%H:%M`, `%d/%m/%Y` (date and time formats) | `khal` display formats. |

Existing calendar data is not migrated automatically. Set `KHAN_WORKSPACE_DIR` (or the Compose host-path variable) to the existing data location explicitly. Do not mount unrelated host directories into the container.

## Development and verification

The supported packaged/runtime path is Docker. For source development, use Python 3.11+ and `uv`:

```bash
uv sync --extra test --dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

The optional integration tests use a real `khal` executable and a writable test workspace:

```bash
uv run pytest --no-cov -m integration
```

CI runs the Python test/lint job and a Docker build with image smoke checks, XDG-state write/ownership verification and MCP stdio conformance.

## Security and privacy

- The container runs as an unprivileged user, exposes no TCP port and uses stdio for MCP.
- Calendar files and exports are local workspace data. Protect the host directory and backups as you would other private schedule data.
- Calendar content is treated as untrusted input; free-text arguments and calendar names are validated.
- The image build excludes local environment files, project metadata, tests and development artifacts.

## License

MIT. See [LICENSE](LICENSE).
