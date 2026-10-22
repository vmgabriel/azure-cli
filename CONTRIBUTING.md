# Contributing to Azure CLI (Internal Tool)

Thanks for taking the time to improve the internal Azure DevOps CLI. The
current focus is Work Items and their linked pull requests; Slack support is
planned. This document explains how the project is organised, how to add a
feature without breaking the architecture, and what a pull request should
contain.

For installation instructions see [`INSTALL.md`](INSTALL.md); for the user
documentation see [`README.md`](README.md).

## Development setup

Requirements: Python 3.11–3.13, `git`, and [Hatch](https://hatch.pypa.io/).

```bash
git clone https://github.com/vmgabriel/azure-cli.git
cd azure-cli
make install
```

`make install` creates the Hatch environment and installs the project in
editable mode with the `dev` extra. The same thing without `make`:

```bash
hatch env create
hatch run python -m pip install -e ".[dev]"
```

Useful commands:

```bash
make test          # unit + integration tests, with coverage
make test-unit     # fast, offline unit tests
make lint          # ruff check, ruff format --check and mypy --strict
make format        # apply the automatic fixes
make clean         # remove caches and build artifacts
```

You can call the tool from the development environment for manual testing:

```bash
hatch run azure-cli --help
hatch run azure-cli list
hatch run azure-cli detail 12345
```

Use the same commands without `hatch run` after installing the package with
`make install`; for example, `azure-cli --help` and `azure-cli list`.

## Architecture rules

The project follows Clean Architecture with screaming package names. Keep the
dependency direction:

```text
presentation ──► application ──► domain
infrastructure ─────────────────► domain
```

- **`domain/`** contains entities, value objects, domain exceptions and the
  ports (interfaces) the outside world must implement. It imports only the
  standard library. It must not import `requests`, `pydantic`, `typer` or
  anything from the other layers.
- **`application/`** contains the use cases and pure services. A use case
  receives its collaborators through the constructor. It may use the domain
  and standard library; it must not read environment variables or open HTTP
  connections.
- **`infrastructure/`** implements the ports: Azure DevOps REST clients, DTOs,
  repositories, HTML cleaning and the HTTP session. This is the only layer that
  knows about `requests` and Azure DevOps payloads.
- **`presentation/`** contains Typer commands, rendering and the dependency
  injection container. Commands translate CLI options into use case calls and
  format the result; they do not contain business rules.
- **`config/`** resolves the settings from the TOML file, the environment and
  `.env`, and validates them.

When a new feature needs data from Azure DevOps, add a method to the relevant
port in `domain/interfaces/`, implement it in `infrastructure/`, and call it
from an application use case. The unit tests should use a fake implementation
of the port, exactly like the existing ones.

## Adding a feature

### A new use case

1. Create `src/azure_cli/application/use_cases/<name>.py`.
2. Declare the dependencies in `__init__` and keep `execute()` free of I/O
   side effects other than the collaborators it was given.
3. Add unit tests in `tests/unit/test_application/` using the fakes from
   `tests/conftest.py`.
4. If the use case needs a new gateway method, update the port and every
   implementation/fake (the type checker will point them out).

### A new CLI command

1. Create a module in `src/azure_cli/presentation/cli/commands/`.
2. Expose `register(app: typer.Typer) -> None` and add the command there.
3. Register it in the loop at the end of `presentation/cli/main.py`.
4. Add it to the `components`/container wiring in
   `presentation/cli/container.py` when it needs a new use case.
5. Add the command to the `test_every_command_is_registered` test and cover the
   success path, the error path and `--help` in
   `tests/unit/test_presentation/test_cli.py`.
6. Update the command table and the usage examples in `README.md`.
7. Check the manual workflow with `hatch run azure-cli <command> --help` and a
   real invocation against a test project.

Commands should return exit code `0` on success and let `cli_errors()` map
configuration, domain and transport failures to exit code `1`; invalid CLI
usage is handled by Typer and exits with `2`.

### A new configuration setting

1. Add the field to `AzureDevOpsSettings` in `config/settings.py`. Add every
   accepted alias to `AliasChoices` so environment variables, the TOML file and
   the CLI keep working.
2. If the setting belongs to a nested TOML section, add the mapping to
   `SECTION_ALIASES` in `config/config_loader.py`.
3. Document it in `README.md` and in `config.example.toml`.
4. Add a unit test in `tests/unit/test_config/`.

Never print a secret. Use `SecretStr` and the existing `masked_*` properties.

### A new HTTP endpoint

1. Add the low-level call to `infrastructure/azure/` or
   `infrastructure/git/`.
2. Map the payload to a domain object in `infrastructure/repositories/`.
3. Translate HTTP errors with the existing domain exceptions
   (`AuthenticationError`, `AzureApiError`, `TransportError`,
   `WorkItemNotFoundError`); do not leak `requests` exceptions.
4. Add unit tests with a mocked response and a stub-server integration test in
   `tests/integration/`.

## Tests

The suite has three layers:

| Layer | Location | Network | Command |
|-------|----------|---------|---------|
| Unit | `tests/unit/` | no | `make test-unit` |
| Integration (stub) | `tests/integration/` | local stub only | `make test` |
| Live integration | `tests/integration/test_*_integration.py` | real Azure DevOps | `make test-integration` |

The live tests are marked `integration` and `live`. They only run when
`--run-live` is passed **and** `AZURE_DEVOPS_PAT` is set; they require
`AZURE_DEVOPS_TEST_WORK_ITEM_IDS` and `AZURE_DEVOPS_DEFAULT_EMAIL` for some
cases. They are read-only, so they never leave test data behind. See the
"Live integration tests" section of the README for the variables.

All new behaviour needs tests:

- Domain rules: a unit test for every branch and validation error.
- Application: a use case test with a fake port.
- Presentation: a `CliRunner` test for the output and the exit code.
- Infrastructure: a mocked-response test and, when practical, a stub-server
  integration test.

Coverage must stay at or above **80%**; `make test` enforces it.

## Style and quality

- Formatting and linting: `make format`, then `make lint`.
- Line length: 100 characters (`ruff`).
- Type hints are mandatory; `mypy --strict` must pass.
- Use `from __future__ import annotations` in new modules.
- Prefer small functions and explicit names; keep the domain free of
  framework types.
- Do not add a dependency unless the standard library and the current
  dependencies cannot do the job; discuss it in the pull request if you do.
- Keep the comments focused on *why*, not on restating the code.

### Pre-commit hooks

Install the hooks once per clone:

```bash
make hooks
# or: hatch run pre-commit install
```

They run ruff, the formatter and mypy on the staged files. Run all of them
manually when needed:

```bash
hatch run pre-commit run --all-files
```

## Documentation

Documentation is part of the change:

- User-facing behaviour and options: `README.md`.
- Installation and Linux troubleshooting: `INSTALL.md`.
- Architecture and contribution workflow: this file.
- Configuration examples: `config/example_config.toml` and
  `config.example.toml`.

If you add a command, option, environment variable or configuration key, update
the README and the examples in the same pull request.

## Commits and pull requests

- Keep commits focused; a commit should build and pass the tests on its own.
- Use an imperative subject, optionally with a conventional prefix:
  `feat: add the links command`, `fix: handle an empty WIQL result`,
  `docs: document the config precedence`, `test: cover the profile merge`.
- Explain *what* changed and *why* in the body; mention the tests you ran.
- Do not commit secrets, `.env` files, `.venv`, coverage files or build
  artifacts.
- Open the pull request against `main` and describe:
  - the user-visible change,
  - the design decisions and trade-offs,
  - the tests you added,
  - anything intentionally left out.

### Pull request checklist

- [ ] `make lint` passes.
- [ ] `make test` passes with coverage ≥ 80%.
- [ ] New behaviour has unit tests and, where relevant, integration tests.
- [ ] `README.md` / `INSTALL.md` / examples are updated.
- [ ] No secrets, credentials or generated files are included.
- [ ] The commit messages explain the change.

## Reporting a problem

Open an issue with:

- the command you ran and the full output (never the token),
- `azure-cli config` (it masks the token),
- `python --version` and the output of `azure-cli --help`,
- your operating system and, for a transport error, whether you are behind a
  proxy.

Small, reproducible examples are the fastest way to get a fix.
