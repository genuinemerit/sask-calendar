# VM setup — sask-dev

Procedure for reconfiguring the existing NixOS VM instance as the sask
development host. All steps are manual. The VM already has NixOS 25.11,
user `dave`, KDE Plasma, and SSH access from the Ubuntu host laptop.

## Prerequisites

On the Ubuntu host laptop:

- SSH access to the VM already works (verify: `ssh dave@<VM-IP>` succeeds)
- `gh` CLI authenticated to GitHub (needed for repo creation, not the VM)

On the NixOS VM:

- GitHub SSH key (`~/.ssh/sask_ed25519`) already in place and registered
  on GitHub (public key: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHzAdM5qhmJBjlH2RwmlyoneJdkIZdqxiS2rTf2OR3XO dave@nixos_sask-001`)
- SSH config at `~/.ssh/config` already routes `github.com` through that key

## 1. Add the Ubuntu host's public key to configuration.nix

On the Ubuntu host, print the public key used to SSH into the VM:

```bash
cat ~/.ssh/<your-key>.pub
```

Open `infra/configuration.nix` in the repo and replace the placeholder
comment in `users.users.dave.openssh.authorizedKeys.keys` with that key:

```nix
openssh.authorizedKeys.keys = [
  "ssh-ed25519 AAAA... dave@ubuntu-host"
];
```

Commit the change before copying to the VM:

```bash
git add infra/configuration.nix
git commit -m "infra: add Ubuntu host authorized key"
```

## 2. Copy configuration.nix to the VM and apply

From the repo root on the Ubuntu host:

```bash
scp infra/configuration.nix dave@<VM-IP>:/tmp/configuration.nix
```

On the VM, apply it:

```bash
sudo cp /tmp/configuration.nix /etc/nixos/configuration.nix
sudo nixos-rebuild switch
```

This will:

- Rename the hostname from `nixos` to `sask-dev`
- Enforce key-only SSH, no root login (REQ-SEC-001)
- Ensure all project packages are present

The hostname change takes effect immediately for new shells. The running
SSH session is unaffected — reconnect after the switch to see `sask-dev`.

## 3. Verify SSH and hostname

Reconnect from the Ubuntu host:

```bash
ssh dave@<VM-IP>
hostname   # should print: sask-dev
```

Confirm password authentication is rejected:

```bash
ssh -o PreferredAuthentications=password dave@<VM-IP>
# should fail: "Permission denied (publickey)"
```

## 4. Clone the repository

On the VM:

```bash
git clone git@github.com:genuinemerit/sask-calendar.git
cd sask-calendar
```

(The VM's `~/.ssh/config` already routes this through `sask_ed25519`.)

## 5. Enter the dev shell and generate lock files

```bash
nix develop
```

Verify the pinned toolchain:

```bash
python3 --version   # 3.12.x
poetry --version
ruff --version
```

Generate and commit lock files:

```bash
nix flake lock

poetry install --no-root
poetry run pip freeze > requirements.txt

git add flake.lock poetry.lock requirements.txt
git commit -m "chore: add lock files generated on sask-dev VM"
git push
```

The VM is now the single source of dev truth. Lock files are committed and
the environment is fully reproducible from a clean clone.
