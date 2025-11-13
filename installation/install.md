# Frappe HRMS Installation on AWS EC2 with Docker

This README provides step-by-step documentation for installing Frappe HRMS on an Amazon EC2 instance using Docker. The process assumes you are using an Amazon Linux instance (e.g., EC2 t2.micro or similar) and have SSH access configured. Frappe HRMS is installed as an app on top of ERPNext, using the Frappe Bench easy-install script.

## Prerequisites

- An AWS EC2 instance running Amazon Linux (or compatible OS).
- SSH key pair for access (e.g., `yaswanth.pem` in this example).
- Basic knowledge of Linux commands and Docker.
- Ensure ports 80 (HTTP) and 443 (HTTPS) are open in your EC2 security group for web access.
- Python 3 installed on the instance (usually pre-installed on Amazon Linux).
- Root or sudo access on the instance.

**Note:** This installation uses the `develop` branch of ERPNext. For production, consider using a stable version (e.g., `--version=version-15`).

## Step-by-Step Installation

### 1. SSH into the EC2 Instance
Connect to your EC2 instance using SSH. Replace the key file and IP with your own.

```
ssh -i ~/.ssh/yaswanth.pem ec2-user@35.178.121.142
```

### 2. Download the Frappe Bench Easy-Install Script
Fetch the installation script from the Frappe repository.

```
wget https://raw.githubusercontent.com/frappe/bench/develop/easy-install.py
```

### 3. Update the System
Update all packages to ensure the system is current. Amazon Linux uses `dnf` (with `yum` as an alias).

```
sudo yum update -y
sudo dnf update -y
```

### 4. Install Docker
Install Docker using the package manager.

```
sudo dnf install docker -y
```

### 5. Enable and Start Docker Service
Configure Docker to start on boot and launch it immediately.

```
sudo systemctl enable docker
sudo systemctl start docker
```

### 6. Add User to Docker Group
Add the current user (`ec2-user`) to the Docker group to run Docker commands without sudo.

```
sudo usermod -aG docker ec2-user
```

### 7. Log Out and SSH Back In
Exit the session and reconnect for group changes to take effect.

```
exit
ssh -i ~/.ssh/yaswanth.pem ec2-user@35.178.121.142
```

### 8. Verify Docker Installation
Check the Docker version to confirm installation.

```
docker version
```

### 9. Install Docker Compose
Set up Docker Compose as a CLI plugin.

```
# Create the plugins directory
mkdir -p ~/.docker/cli-plugins/

# Download the compose plugin
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o ~/.docker/cli-plugins/docker-compose

# Make it executable
chmod +x ~/.docker/cli-plugins/docker-compose
```

### 10. Verify Docker Compose
Check the Docker Compose version.

```
docker compose version
```

Log out and SSH back in if needed for changes to apply.

```
exit
ssh -i ~/.ssh/yaswanth.pem ec2-user@35.178.121.142
```

### 11. Deploy ERPNext Using Easy-Install Script
Run the script to deploy ERPNext (base for HRMS). Replace `--email` and `--sitename` with your values.

```
python3 easy-install.py deploy --email=admin@mailinator.com --sitename=gvs-uat.lykkeworks.com --app=erpnext --version=develop
```

This sets up a Docker-based Frappe environment with ERPNext.

### 12. Access the Frappe Backend Container
Enter the running Frappe backend container.

```
docker exec -it frappe-backend-1 bash
```

### 13. Verify Bench Version
Inside the container, check the Bench version.

```
bench version
```

### 14. Get the HRMS App
Fetch the HRMS app repository.

```
bench get-app hrms
```

Verify the Bench version again if needed.

```
bench version
```

### 15. Run Database Migrations
Apply migrations for the site.

```
bench --site gvs-uat.lykkeworks.com migrate
```

### 16. Restart Bench
Restart the Bench processes.

```
bench restart
```

### 17. Restart the Container
Exit the container and restart it.

```
exit
docker restart frappe-backend-1
```

### 18. Install HRMS App on the Site
Re-enter the container and install HRMS on the specific site.

```
docker exec -it frappe-backend-1 bash
bench --site gvs-uat.lykkeworks.com install-app hrms
```

Exit the container and the SSH session.

```
exit
exit
```

## Post-Installation

- Access the site at `http://<your-ec2-public-ip>` or the domain specified (e.g., `gvs-uat.lykkeworks.com`).
- Default login: Use the email provided (e.g., `admin@mailinator.com`). The password is auto-generated and emailed or logged—check your email or container logs.
- For production, configure SSL, backups, and monitoring.
- To update: Use `bench update` inside the container.

## Troubleshooting

- **Permission Issues:** Ensure you're in the Docker group.
- **Container Not Found:** Verify container name with `docker ps`.
- **Migration Errors:** Check logs with `docker logs frappe-backend-1`.
- **Network Issues:** Confirm EC2 security groups allow inbound traffic.

For more details, refer to the official Frappe documentation: https://frappeframework.com/docs or https://erpnext.com/docs.
