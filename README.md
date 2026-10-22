# Azure CLI (Internal Tool)

An internal, general-purpose command-line tool for **Azure DevOps**. It
currently handles **Work Items**, including their linked **PRs** (pull
requests) and branches, with **future Slack integrations** planned.

```bash
azure-cli --help
azure-cli list
azure-cli detail 1234
```

```text
📄 ID: 1234 | Estado: Active
🔗 URL: https://dev.azure.com/acme/widgets/_workitems/edit/1234
🏷️  Título: Login fails on Safari
🧩 Tipo: Bug
📍 Área: Acme/Frontend
🔄 Iteración: Acme/Sprint 12
👤 Asignado a: Ada Lovelace
⭐ Puntos: 3
🏷️  Tags: frontend, p1
```

## Features

- List the work items assigned to you, or search the whole project.
- Show the full detail of a work item, including description, acceptance
  criteria, tags and story points.
- Create, update and comment work items.
- Show the pull requests and branches related to a work item.
- Human-readable tables and machine-readable JSON.
- Layered configuration: CLI flags, environment, `.env`, TOML file, defaults.
- Profiles for several organizations or projects.
- Planned: Slack integrations, starting with configurable channel and token
  settings in the TOML file.

The current command surface focuses on work items. Pull requests are exposed
through the `links` command and the related artifacts of `detail` and
`get --links`; Slack support is reserved for a future release.

## Installation

### Requirements

- Python **3.11**, **3.12** or **3.13**.
- An Azure DevOps organization and project.
- A personal access token (PAT) with access to the work items and, for the
  `links`/`detail` commands, to the project's code.

### pipx (recommended for a CLI)

The distribution is named `azure-cli` and exposes the `azure-cli` command.
[pipx](https://pipx.pypa.io/) installs it in its own virtual environment and
puts `azure-cli` on your `PATH`:

```bash
pipx install .
```

> The distribution name is `azure-cli`, which is also the name used by
> Microsoft's official Azure CLI on PyPI. Install this internal tool from a
> checkout until it is published under a distinct distribution name.

If `azure-cli` is not found afterwards, run `pipx ensurepath` and open a new
terminal.

### pip

```bash
python -m pip install .
```

A virtual environment is recommended:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install .
```

### Hatch (development install)

[Hatch](https://hatch.pypa.io/) provides the isolated environments used by the
Makefile:

```bash
pipx install hatch
git clone https://github.com/vmgabriel/azure-cli.git
cd azure-cli
make install            # hatch env create + editable install with dev extras
hatch run azure-cli --help
```

Without `make`:

```bash
hatch env create
hatch run python -m pip install -e ".[dev]"
```

### Verify the installation

```bash
azure-cli --help
```

If the command is not found, check that the scripts directory of your Python
or pipx installation is on `PATH` (`pipx ensurepath` for pipx).

## Configuration

### 1. Create the configuration file

The default location is `~/.azure_cli/config.toml`:

```bash
mkdir -p ~/.azure_cli
cp config/example_config.toml ~/.azure_cli/config.toml
```

To use another file, point `AZURE_CLI_CONFIG_PATH` at it:

```bash
export AZURE_CLI_CONFIG_PATH="$HOME/projects/azure-cli/config.example.toml"
```

The previous `AZURE_DEVOPS_CONFIG_FILE` variable is still accepted.

The file is optional when every setting comes from the environment.

### 2. Example `config.toml`

The full example lives in [`config.example.toml`](config.example.toml); the
minimal one is [`config/example_config.toml`](config/example_config.toml).
Both use the recommended nested sections:

```toml
# ~/.azure_cli/config.toml

[azure]
org = "serviciosfintech"
project = "bold"
api_version = "7.1"

[user]
# Default assignee of `azure-cli list`. `azure-cli mine` does not need it:
# Azure DevOps resolves the current user with the `@me` macro.
email = "gabriel.vargas@bold.co"

# Optional: reserved for a future Slack integration.
[slack]
channel = "#workitems"
token = ""
```

The flat keys accepted by older versions (`azure_org`, `azure_project`,
`pat_token`, `default_email`, `slack_channel`, `slack_token`, `timeout`,
`output_format`, `base_url`) still work. A file can also declare profiles:

```toml
[profiles.work.azure]
org = "serviciosfintech"
project = "bold"

[profiles.personal.azure]
org = "my-org"
project = "side-project"
```

Select one with `azure-cli --profile work list` or
`AZURE_CLI_PROFILE=work azure-cli list`.

### 3. Set the personal access token

Create a PAT in Azure DevOps: **User settings → Personal access tokens → New
Token**. Grant at least **Work Items (Read & Write)**. Grant **Code (Read)**
as well if you want the `links` and `detail` commands to find pull requests and
branches.

Export the token instead of writing it to the configuration file:

```bash
export AZURE_DEVOPS_PAT="your-personal-access-token"
```

Add that line to `~/.bashrc`, `~/.zshrc` or your shell's profile to persist it.
The token can also live in a project-local `.env` file:

```dotenv
AZURE_DEVOPS_PAT=your-personal-access-token
AZURE_DEVOPS_ORGANIZATION=serviciosfintech
AZURE_DEVOPS_PROJECT=bold
```

> **Keep the token secret.** Never commit it. Prefer `AZURE_DEVOPS_PAT` over
> `--pat`: a flag ends up in your shell history and in the process list.
> `azure-cli config` only prints the last four characters.

### Precedence

The highest priority wins:

1. CLI flags — `--org`, `--project`, `--pat`, `--api-version`, `--timeout`,
   `--output`, `--profile`
2. environment variables — `AZURE_DEVOPS_*` for the connection and
   `AZURE_CLI_*` for tool settings
3. the `.env` file of the current directory
4. the TOML configuration file
5. built-in defaults (`serviciosfintech`, `bold`, API version `7.1`,
   timeout `15` seconds, text output)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AZURE_DEVOPS_ORGANIZATION` | yes* | `serviciosfintech` | Organization of `https://dev.azure.com/<org>` |
| `AZURE_DEVOPS_PROJECT` | yes* | `bold` | Team project holding the work items |
| `AZURE_DEVOPS_PAT` | yes | | Personal access token |
| `AZURE_DEVOPS_API_VERSION` | no | `7.1` | REST API version |
| `AZURE_DEVOPS_TIMEOUT` | no | `15` | HTTP timeout in seconds |
| `AZURE_DEVOPS_OUTPUT_FORMAT` | no | `text` | `text` or `json` |
| `AZURE_DEVOPS_DEFAULT_EMAIL` | no | | E-mail used by `list`; `mine` resolves the user with `@me` |
| `AZURE_DEVOPS_BASE_URL` | no | | Override the API root (Azure DevOps Server) |
| `AZURE_CLI_CONFIG_PATH` | no | `~/.azure_cli/config.toml` | Path to the TOML file |
| `AZURE_CLI_PROFILE` | no | `default` | Profile of the TOML file |
| `AZURE_DEVOPS_CONFIG_FILE` | no | | Legacy alias of `AZURE_CLI_CONFIG_PATH` |
| `AZURE_DEVOPS_PROFILE` | no | | Legacy alias of `AZURE_CLI_PROFILE` |

\* The defaults are useful for the project this tool was written for; set them
explicitly for any other organization or project.

Check the resolved configuration at any time:

```bash
azure-cli config
```

## Usage

```bash
# the work items assigned to you, most recently changed first
azure-cli mine
azure-cli mine --format table --limit 10
azure-cli mine --format json

# the work items of the project
azure-cli list
azure-cli list --format json
azure-cli list --state Active --assigned-to "Ada Lovelace" --tag frontend
azure-cli list --search "login" --top 20
azure-cli list --closed

# a single work item
azure-cli detail 12345
azure-cli detail 12345 --format json
azure-cli get 12345 --links

# create, update and comment
azure-cli create --type Bug --title "Login fails on Safari" --tag frontend --story-points 3
azure-cli update 12345 --state "Ready for testing"
azure-cli update 12345 --acceptance-criteria "<ul><li>The user can log in</li></ul>"
azure-cli comment 12345 "Reproduced on Safari 18."

# the git artifacts connected to a work item
azure-cli links 12345

# help
azure-cli --help
azure-cli list --help
azure-cli detail --help
```

| Command | Description |
|---------|-------------|
| `list` | List or search the work items of the project. |
| `mine` | The active work items assigned to you (`workitems` is an alias). |
| `detail` | Show one work item with its content and git artifacts. |
| `get` | Show one work item (`--links` adds the git relations). |
| `create` | Create a work item. |
| `update` | Change the fields of a work item. |
| `comment` | Add a comment to a work item. |
| `links` | List the pull requests and branches related to a work item. |
| `config` | Show the resolved configuration (the PAT is masked). |

> The single-work-item command is `detail <id>` (the older `get <id>` command
> also works and `--links` adds the related artifacts). The `workitems`
> command is an alias of `mine`, not a command group.

`list`, `mine` and `detail` accept `--format table|json`; without it they
follow the global `--output` option. The tables colour the state of every work
item, and the colours are dropped when the output is piped or `NO_COLOR` is set.

Exit codes: `0` success · `1` configuration, domain or transport failure ·
`2` CLI usage error.

## Architecture

The code is organised by *architectural purpose*: the folder names tell you
what the system does before you read a single line.

```text
src/azure_cli/
├── domain/          # Business rules: work items, states, tags, ports
│   ├── entities/    #   WorkItem, RelatedLink, WorkItemComment
│   ├── value_objects/  # WorkItemId, WorkItemState, WorkItemType, Tag, LinkKind
│   └── interfaces/  #   WorkItemRepository, GitRepository, AzureDevOpsGateway
├── application/     # Use cases and services built on the domain
│   ├── use_cases/   #   GetWorkItem, ListWorkItems, ListMyWorkItemsUseCase, ...
│   └── services/    #   WIQL builder, field spec, work item draft, selection
├── infrastructure/  # Adapters talking to the outside world
│   ├── azure_client.py  # AzureDevOpsClient: one call, one domain object
│   ├── html_utils.py    # clean_html: rich text to plain text
│   ├── exceptions.py    # Infrastructure specific errors
│   ├── azure/       #   Work item REST client, DTOs, HTML cleaning
│   ├── git/         #   Pull request REST client
│   ├── http/        #   Authenticated session factory
│   └── repositories/    # AzureWorkItemRepository, AzureGitRepository
├── presentation/    # The Typer commands
│   ├── main.py      #   The console script entry point (`app`)
│   └── cli/         #   main.py, container.py, console.py, formatters.py, commands/
└── config/          # Configuration: env vars, .env, config.toml
```

- **Clean Architecture** — dependencies point inwards only:
  `presentation → application → domain` and `infrastructure → domain`.
  The domain imports nothing but the standard library.
- **Screaming Architecture** — `use_cases/get_work_item.py`,
  `repositories/azure_work_item_repository.py` and `presentation/cli/commands/`
  tell the story of the tool at a glance.
- **Ports & adapters** — the domain declares the interfaces it needs
  (`domain/interfaces/`); the infrastructure implements them and the unit tests
  fake them. The unit tests never touch the network; the live integration
  tests that call the real API are opt-in.
- **Dependency injection** — the use cases receive their collaborators
  through their constructor: the gateway port for Azure DevOps, the settings
  for the identity of the user. They are never built inside.

## Development

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full contribution workflow
and [`INSTALL.md`](INSTALL.md) for a detailed Linux setup.

Everything runs inside [Hatch](https://hatch.pypa.io/) environments:

| Command | Description |
|---------|-------------|
| `make install` | Editable install + dev dependencies via Hatch |
| `make hooks` | Install the pre-commit git hooks |
| `make test` | All tests with coverage (fails below 80%) |
| `make test-unit` | Unit tests only |
| `make test-integration` | Integration tests, including the live ones |
| `make lint` | ruff check + ruff format (check) + mypy `--strict` |
| `make format` | Apply ruff fixes and formatting |
| `make build` | Build sdist + wheel via Hatch |
| `make clean` | Remove artifacts and caches |

The unit tests are deterministic and offline: they use fake repositories. The
integration tests run the real HTTP stack against a stub Azure DevOps server
(`tests/integration/stub_server.py`). The **live** integration tests call the
real Azure DevOps API; they are opt-in and never run as part of `make test`.

### Running the tests

```bash
make test          # unit + stub integration, with coverage
make test-unit     # unit tests only
make lint          # ruff + mypy
make format        # autofix and format
```

Or straight from Hatch:

```bash
hatch run test
hatch run test-unit
hatch run lint
```

### Live integration tests

`make test-integration` enables them with `--run-live`. They are skipped when
`AZURE_DEVOPS_PAT` is not set, and the individual tests are skipped when the
data they need is not configured. They are read-only — list, detail and
related artifacts — so they never create, update or delete anything.

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_DEVOPS_PAT` | yes | PAT with read access to work items |
| `AZURE_DEVOPS_ORGANIZATION` | yes | Organization to query (or the TOML file) |
| `AZURE_DEVOPS_PROJECT` | yes | Team project to query (or the TOML file) |
| `AZURE_DEVOPS_TEST_WORK_ITEM_IDS` | yes | Comma-separated known work item ids, e.g. `1234,5678` |
| `AZURE_DEVOPS_DEFAULT_EMAIL` | yes | E-mail whose work items are listed (`AZURE_DEVOPS_TEST_EMAIL` also works) |
| `AZURE_DEVOPS_TIMEOUT` | no | Per-call timeout; the live tests cap it at 30 seconds |

```bash
export AZURE_DEVOPS_PAT=...
export AZURE_DEVOPS_ORGANIZATION=acme
export AZURE_DEVOPS_PROJECT=widgets
export AZURE_DEVOPS_TEST_WORK_ITEM_IDS=1234,5678
export AZURE_DEVOPS_DEFAULT_EMAIL=ada@acme.com

make test-integration
```

To run only the live tests, bypassing the stub ones:

```bash
hatch run pytest tests/integration -m live --run-live
```

### Pre-commit hooks

The repository ships a [pre-commit](https://pre-commit.com/) configuration that
runs ruff, the formatter and mypy before every commit:

```bash
make hooks                                  # install the git hook
hatch run pre-commit run --all-files        # check the whole tree now
```

### Contributing

1. Fork the repository and create a feature branch.
2. Install the development environment with `make install`.
3. Add or update tests with your change.
4. Run `make lint` and `make test`.
5. Open a pull request describing the behaviour and the tests you added.

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) for the architecture rules and the
detailed checklist.

## Troubleshooting

### `azure-cli` is not found

The scripts directory is not on `PATH`. With pipx run `pipx ensurepath` and
open a new terminal; with pip use the `bin` directory of the active virtual
environment (`python -m site --user-base`).

### `Missing configuration: pat (AZURE_DEVOPS_PAT)`

The token is not visible to the process. Export it in the current shell:

```bash
export AZURE_DEVOPS_PAT="your-personal-access-token"
```

A token defined in `~/.bashrc` is not available in an already open terminal
until you reload it (`source ~/.bashrc`) or open a new one.

### Authentication error (HTTP 401/403)

- The PAT expired or was revoked: create a new one.
- The token belongs to another organization: recreate it for the organization
  in `AZURE_DEVOPS_ORGANIZATION`.
- A scope is missing: grant **Work Items (Read & Write)** and, for related
  pull requests and branches, **Code (Read)**.
- The organization slug or project name is wrong: `azure-cli config` prints the
  resolved API base URL.

### The configuration file is ignored

- The file must be named `config.toml` and live in `~/.azure_cli/`.
- `AZURE_CLI_CONFIG_PATH` overrides the location; check
  `echo "$AZURE_CLI_CONFIG_PATH"`. The legacy `AZURE_DEVOPS_CONFIG_FILE`
  variable is still accepted.
- Environment variables and a `.env` file win over the TOML file.
- `azure-cli config` shows the profile and the URL that were actually used.

### `Unknown configuration profile`

The requested profile is not declared in the file. List the profiles with
`grep '^\[profiles\.' ~/.azure_cli/config.toml`, or remove
`--profile`/`AZURE_CLI_PROFILE` to use the `default` profile.

### Requests time out or the connection fails

Increase the timeout (`--timeout 60` or `AZURE_DEVOPS_TIMEOUT=60`). Behind a
corporate proxy, export the standard variables (`HTTPS_PROXY`, `NO_PROXY`);
`requests` honours them. Check that `https://dev.azure.com` is reachable.

### The `links` command returns nothing

The work item may have no linked pull requests or branches. If you expected
some, confirm that the PAT can read the repository (**Code (Read)**) and that
the branch or PR mentions the work item id (for example `AB#12345`).

### `make test-integration` skips the live tests

The live tests need both `--run-live` (the Makefile passes it) and a non-empty
`AZURE_DEVOPS_PAT`. Some tests additionally require
`AZURE_DEVOPS_TEST_WORK_ITEM_IDS` and `AZURE_DEVOPS_DEFAULT_EMAIL`; the skip
messages say which variable is missing.

### `make install` or `make lint` fails

Install Hatch first (`pipx install hatch`) and check `python --version` — the
project supports Python 3.11 to 3.13. Run `make format` to fix the automatic
ruff findings, then `make lint` again.

## License

MIT
