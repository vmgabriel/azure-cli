# Installing Azure CLI (Internal Tool) on Linux

This guide covers a complete Linux setup for the internal Azure DevOps CLI:
Python, the `azure-cli` command, the personal access token and the
configuration file. The tool currently manages work items and their linked
pull requests and branches; Slack integrations are planned. It works on
Debian/Ubuntu, Fedora/RHEL and Arch, on x86_64 and aarch64. Windows users can
run the same steps inside WSL.

For a one-page command reference see [`README.md`](README.md); for the
contribution workflow see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## 1. Requirements

- Linux with a POSIX shell (bash or zsh).
- Python **3.11**, **3.12** or **3.13**.
- `pip` and `venv` for your Python installation.
- An Azure DevOps organization and project.
- A personal access token (PAT), created in step 4.

Check what you already have:

```bash
python3 --version
python3 -m pip --version
git --version
```

If Python is older than 3.11, install a newer one first.

## 2. Install Python and pipx

### Debian / Ubuntu

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip pipx git
```

### Fedora / RHEL

```bash
sudo dnf install -y python3 python3-pip pipx git
```

### Arch

```bash
sudo pacman -S --needed python python-pip python-pipx git
```

After installing pipx, make its application directory available on `PATH`:

```bash
pipx ensurepath
```

Open a new terminal (or `source ~/.bashrc`) before continuing.

## 3. Install the command

### Option A — pipx (recommended)

The project is distributed as `azure-cli` and exposes the `azure-cli` command.
pipx keeps it in its own virtual environment, so it cannot break other Python
tools:

```bash
pipx install .
```

> The distribution name is `azure-cli`, which is also used by Microsoft's
> official Azure CLI on PyPI. Install this internal tool from a checkout until
> it is published under a distinct distribution name.

Verify:

```bash
azure-cli --help
```

To upgrade later, pull the checkout and reinstall it:

```bash
git pull
pipx install --force .
```

### Option B — pip in a virtual environment

Use this when you want full control over the environment:

```bash
python3 -m venv ~/.venvs/azure-cli
source ~/.venvs/azure-cli/bin/activate
python -m pip install --upgrade pip
python -m pip install .
azure-cli --help
```

Add the environment to your shell only when you need the command:

```bash
# ~/.bashrc or ~/.zshrc
alias azure-cli="$HOME/.venvs/azure-cli/bin/azure-cli"
```

### Option C — Hatch (development)

Use this when you want to change the code, run the tests or use the Makefile:

```bash
pipx install hatch
git clone https://github.com/vmgabriel/azure-cli.git
cd azure-cli
make install
```

`make install` runs `hatch env create` and installs the project in editable
mode together with the development extras. You can always run the tool through
Hatch:

```bash
hatch run azure-cli --help
```

The equivalent commands without `make` are:

```bash
hatch env create
hatch run python -m pip install -e ".[dev]"
```

### Arch Linux (makepkg / AUR)

Install the build prerequisites:

```bash
sudo pacman -S --needed base-devel python-build python-installer
```

Clone the repository, enter it and build the package from the included
`PKGBUILD`:

```bash
git clone https://github.com/vmgabriel/azure-cli.git
cd azure-cli
makepkg -si
```

`makepkg -si` builds the package, installs it with `pacman` and resolves its
dependencies.

> Once the package is published to the AUR, you will be able to install it
> directly with `yay -S azure-cli` or `paru -S azure-cli`.

After installation, create `~/.azure_cli/config.toml` as described in step 6
and export your personal access token as described in step 5:

```bash
export AZURE_DEVOPS_PAT="your-personal-access-token"
```

Then verify the command:

```bash
azure-cli --help
```

## 4. Create a personal access token

1. Open `https://dev.azure.com/<your-organization>`.
2. Click **User settings** (the person icon, top right) → **Personal access
   tokens** → **New Token**.
3. Select the organization and the expiration date.
4. Grant these scopes:
   - **Work Items → Read & Write** — required for every command.
   - **Code → Read** — required by `azure-cli links` and
     `azure-cli detail` to find pull requests and branches.
   - **Project and Team → Read** — recommended; avoids permission surprises
     when the project metadata is resolved.
5. Create the token and copy it immediately. Azure DevOps shows it only once.
6. Store it in your password manager or a secret manager.

> The token is a password. Do not put it in a repository, a ticket, a chat
> message or a shell script that is committed to git.

## 5. Export the token

```bash
export AZURE_DEVOPS_PAT="your-personal-access-token"
```

To persist it for interactive shells, add the same line to `~/.bashrc` or
`~/.zshrc`, then reload the file:

```bash
source ~/.bashrc
```

For a project, a local `.env` file is also supported:

```dotenv
AZURE_DEVOPS_PAT=your-personal-access-token
AZURE_DEVOPS_ORGANIZATION=serviciosfintech
AZURE_DEVOPS_PROJECT=bold
```

Make sure `.env` is listed in `.gitignore`. The tool never prints the token;
`azure-cli config` shows only its last four characters.

## 6. Create the configuration file

The default location is `~/.azure_cli/config.toml`. From a source checkout:

```bash
mkdir -p ~/.azure_cli
cp config/example_config.toml ~/.azure_cli/config.toml
chmod 600 ~/.azure_cli/config.toml
```

If you installed from a package and do not have the repository at hand, create
the file directly:

```bash
mkdir -p ~/.azure_cli
cat > ~/.azure_cli/config.toml <<'EOF'
[azure]
org = "serviciosfintech"
project = "bold"
api_version = "7.1"

[user]
email = "you@company.com"

[slack]
channel = "#workitems"
token = ""
EOF
chmod 600 ~/.azure_cli/config.toml
```

Replace `org`, `project` and `email` with your values. The PAT is intentionally
not part of this file; export it as shown in step 5.

To use a configuration file from another location:

```bash
export AZURE_CLI_CONFIG_PATH="$HOME/projects/azure-cli/config.example.toml"
```

The previous `AZURE_DEVOPS_CONFIG_FILE` variable is still accepted.

Configuration precedence, highest first:

1. CLI flags (`--org`, `--project`, `--pat`, `--profile`, ...)
2. environment variables (`AZURE_DEVOPS_*` for the connection, `AZURE_CLI_*`
   for the tool)
3. the `.env` file of the current directory
4. the TOML configuration file
5. built-in defaults

## 7. Verify

```bash
# the available commands
azure-cli --help

# the token, organization, project and profile that were resolved
azure-cli config

# the work items assigned to you
azure-cli mine

# a project-wide search
azure-cli list --state Active --top 5

# one work item and the git artifacts it is linked to
azure-cli detail 12345
azure-cli links 12345
```

`azure-cli config` never prints the full token. If it reports
`Missing configuration: pat`, the environment variable is not visible to the
current shell; see step 5.

## 8. Upgrade and uninstall

Upgrade from the checkout with pipx:

```bash
git pull
pipx install --force .
```

Uninstall the command but keep the configuration:

```bash
pipx uninstall azure-cli
```

Remove the configuration directories only if you no longer need them:

```bash
rm -rf ~/.azure_cli
```

## 9. Common installation problems

| Symptom | Fix |
|---------|-----|
| `azure-cli: command not found` | Run `pipx ensurepath`, open a new terminal, or activate the virtual environment. |
| `python3: command not found` | Install Python 3.11+ with your package manager. |
| `No module named venv` | Install the `python3-venv` package (Debian/Ubuntu). |
| `make: command not found` | Hatch route: install `make`, or run the `hatch` commands directly. |
| `hatch: command not found` | `pipx install hatch`, then `pipx ensurepath`. |
| `externally-managed-environment` from pip | Use pipx or a virtual environment instead of the system Python. |
| HTTP 401 / 403 | Recreate the PAT with the scopes listed in step 4 and check the organization slug. |
| Configuration ignored | Check the path and `AZURE_CLI_CONFIG_PATH`; `azure-cli config` shows what was used. |
| Timeout / proxy error | Set `AZURE_DEVOPS_TIMEOUT=60` and the standard `HTTPS_PROXY`/`NO_PROXY` variables. |

For more troubleshooting see the section of the same name in
[`README.md`](README.md). If the problem persists, open an issue with the
output of `azure-cli --help`, `azure-cli config` (never paste the token) and the
full traceback or error message.
