# SANGAD — Local Host Setup Notes
## Based on architecture v0.3 (ADR-18, ADR-20)

### Host Requirements
- Ubuntu 24.04 LTS (bare metal or VM)
- 16 GB RAM recommended (8 GB minimum)
- 100 GB+ SSD, second physical disk for backups
- Full-disk encryption (LUKS)

### Docker Installation
```bash
sudo apt update && sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo tee /etc/apt/keyrings/docker.asc
echo "deb [arch=amd64] https://download.docker.com/linux/ubuntu noble stable" | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io
```

### Coolify Installation
```bash
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
```
- Access dashboard at http://localhost:8000
- Set long password + 2FA, disable registration
- Add localhost server (built-in)

### Loopback Configuration
- All services bind to 127.0.0.1
- Configure Docker daemon to use loopback for published ports
- Host firewall: `sudo ufw enable && sudo ufw default deny incoming`

### Auto-Start
```bash
sudo systemctl enable docker
sudo systemctl enable coolify
sudo systemctl disable sleep.target suspend.target hibernate.target
```

### Backup Disk
- Mount second disk at /mnt/backup-disk
- Schedule nightly: `0 2 * * * /opt/sangad/infra/scripts/offdisk-backup.sh`