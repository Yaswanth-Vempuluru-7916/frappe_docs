
# Initial Server Setup: Installing Docker and Docker Compose - December 23, 2025

This document records the initial setup steps performed on a fresh Ubuntu server to install Docker and Docker Compose. These steps were likely executed as preparation for deploying the Frappe/ERPNext environment using frappe_docker.

## Server Details
- **OS**: Ubuntu (version not specified in logs, but later confirmed as 24.04.3 LTS)
- **User**: Root or a user with sudo privileges

## Performed Steps (Exact Sequence)

```bash
wget https://raw.githubusercontent.com/frappe/bench/develop/easy-install.py
```
> Downloaded the Frappe easy-install script (for reference or potential future use).

```bash
sudo apt update -y
```

```bash
sudo apt upgrade -y
```
> Updated and upgraded all system packages.

```bash
sudo systemctl enable docker
```

```bash
sudo apt install docker.io -y
```
> Installed Docker.

```bash
sudo systemctl enable docker
```
> (Repeated) Ensured Docker service starts on boot.

```bash
sudo systemctl start docker
```
> Started the Docker service immediately.

```bash
sudo usermod -aG docker $USER
```
> Added the current user to the docker group to allow running Docker commands without sudo.

```bash
mkdir -p ~/.docker/cli-plugins
```

```bash
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o ~/.docker/cli-plugins/docker-compose
```
> Downloaded the latest Docker Compose binary.

```bash
chmod +x ~/.docker/cli-plugins/docker-compose
```
> Made the Docker Compose binary executable.

```bash
docker --version
```
> Verified Docker installation.

```bash
docker compose version
```
> Verified Docker Compose installation.

```bash
exit
```
> Logged out of the session (or exited sudo/su if applicable).

```bash
ls
```
> Listed files in the current directory (likely to check for the downloaded easy-install.py).

## Notes
- These steps set up a standard Docker + Docker Compose environment on Ubuntu.
- The addition of the user to the `docker` group requires a new login/session for the change to take effect.
- The Frappe easy-install.py script was downloaded but not executed in these steps — it may have been used later or kept for reference.
- This setup is a prerequisite for running the official `frappe_docker` deployment.

**Docker and Docker Compose installation completed on December 23, 2025.**
```
