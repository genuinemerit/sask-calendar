{ config, pkgs, ... }:

{
  imports = [
    ./hardware-configuration.nix
  ];

  # ── Boot — BIOS/MBR, virtio disk ────────────────────────────────────────────
  boot.loader.grub.enable = true;
  boot.loader.grub.device = "/dev/vda";
  boot.loader.grub.useOSProber = true;

  # ── System ───────────────────────────────────────────────────────────────────
  system.stateVersion = "25.11";
  networking.hostName = "sask-dev";
  networking.networkmanager.enable = true;

  # ── Locale ───────────────────────────────────────────────────────────────────
  time.timeZone = "Europe/Madrid";
  i18n.defaultLocale = "en_US.UTF-8";
  i18n.extraLocaleSettings = {
    LC_ADDRESS        = "es_ES.UTF-8";
    LC_IDENTIFICATION = "es_ES.UTF-8";
    LC_MEASUREMENT    = "es_ES.UTF-8";
    LC_MONETARY       = "es_ES.UTF-8";
    LC_NAME           = "es_ES.UTF-8";
    LC_NUMERIC        = "es_ES.UTF-8";
    LC_PAPER          = "es_ES.UTF-8";
    LC_TELEPHONE      = "es_ES.UTF-8";
    LC_TIME           = "es_ES.UTF-8";
  };

  # ── Desktop — KDE Plasma 6 on X11 ────────────────────────────────────────────
  services.xserver.enable = true;
  services.displayManager.sddm.enable = true;
  services.desktopManager.plasma6.enable = true;
  services.xserver.xkb = {
    layout  = "us";
    variant = "";
  };
  services.printing.enable = true;

  # ── Audio ─────────────────────────────────────────────────────────────────────
  services.pulseaudio.enable = false;
  security.rtkit.enable = true;
  services.pipewire = {
    enable            = true;
    alsa.enable       = true;
    alsa.support32Bit = true;
    pulse.enable      = true;
  };

  # ── QEMU / SPICE (VM guest utilities) ────────────────────────────────────────
  services.qemuGuest.enable = true;
  services.spice-vdagentd.enable = true;
  systemd.user.services.spice-vdagent = {
    description = "Spice user agent";
    after       = [ "graphical-session.target" ];
    wantedBy    = [ "graphical-session.target" ];
    partOf      = [ "graphical-session.target" ];
    serviceConfig = {
      ExecStart = "${pkgs.spice-vdagent}/bin/spice-vdagent -x";
      Restart   = "on-failure";
    };
  };

  # ── Users ─────────────────────────────────────────────────────────────────────
  users.users.dave = {
    isNormalUser = true;
    description  = "dave";
    extraGroups  = [ "networkmanager" "wheel" ];
    packages = with pkgs; [
      kdePackages.kate
    ];
    openssh.authorizedKeys.keys = [
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMnPtCXhzdNxO4SPuS/rz7NE6BwcQSVJVc+3Lenvtd9V pq_rfw@pm.me"
    ];
  };

  # ── SSH — key-only, no root login (REQ-SEC-001) ───────────────────────────────
  services.openssh = {
    enable   = true;
    settings = {
      PasswordAuthentication = false;
      PermitRootLogin        = "no";
    };
  };
  programs.ssh.startAgent = true;

  # ── Nix settings ──────────────────────────────────────────────────────────────
  nix.settings.experimental-features = [ "nix-command" "flakes" ];
  nixpkgs.config.allowUnfree = true;

  # ── System packages ───────────────────────────────────────────────────────────
  programs.firefox.enable = true;

  environment.systemPackages = with pkgs; [
    bat
    black
    brave
    claude-code
    curl
    eza
    fd
    fzf
    git
    glances
    httpie
    jq
    lazygit
    neovim
    openssh
    openssl
    opentofu
    poetry
    procs
    python312
    ripgrep
    ruff
    sqlite
    wget
  ];
}
