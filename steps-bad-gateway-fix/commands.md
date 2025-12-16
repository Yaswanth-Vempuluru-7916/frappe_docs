```bash
root@Ubuntu-2404-noble-amd64-base ~ # history
    1  reboot
    2  clear
    3  nano ~/.ssh/authorized_keys
    4  chmod 600 ~/.ssh/authorized_keys
    5  exit
    6  ls
    7  exit
    8  wget https://raw.githubusercontent.com/frappe/bench/develop/easy-install.py
    9  ls
   10  sudo yum update -y
   11  sudo dnf update -y
   12  sudo apt update -y
   13  sudo apt upgrade -y
   14  sudo apt install docker.io -y
   15  sudo systemctl enable docker
   16  sudo systemctl start docker
   17  sudo usermod -aG docker $USER
   18  mkdir -p ~/.docker/cli-plugins
   19  curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64   -o ~/.docker/cli-plugins/docker-compose
   20  chmod +x ~/.docker/cli-plugins/docker-compose
   21  docker --version
   22  docker compose version
   23  exit
   24  python3 easy-install.py deploy --email=admin@mailinator.com --sitename=hris-gvs.possibleworks.com --app=erpnext --version=develop
   25  ls
   26  cat frappe.env
   27  docker exec -it frappe-backend-1 bash
   28  docker restart frappe-backend-1
   29  docker exec -it frappe-backend-1 bash
   30  exit
   31  docker ps
   32  docker exec -it frappe-backend-1 bash
   33  ls
   34  cat frappe.env
   35  exir
   36  exit
   37  ls
   38  exit
   39  clear
   40  history
   41  cat frappe.env
   42  lsof -i :8080
   43  lsof -i :900
   44  lsof -i :9000
   45  docker ps
   46  curl -I https://95.216.41.57/
   47  curl -I https://95.216.41.57/curl -Ik https://95.216.41.57/
   48  clear
   49  curl -Ik https://95.216.41.57/
   50  curl -Ik https://localhsot/
   51  curl -Ik https://localhost/
   52  sudo nano /etc/hosts
   53  dig hris-gvs.possibleworks.com +short
   54  sudo nano /etc/hosts
   55  dig hris-gvs.possibleworks.com +short
   56  docker ps
   57  docker logs frappe-backend-1 --tail=100
   58  docker exec -it frappe-backend-1 bench list-sites
   59  docker exec -it frappe-backend-1 bench --site hris-gvs.possibleworks.com install-app erpnext
   60  docker exec -it frappe-backend-1 bench --site hris-gvs.possibleworks.com console
   61  docker exec -it frappe-backend-1 bench --site hris-gvs.possibleworks.com migrate
   62  docker exec -it frappe-backend-1 bench --site hris-gvs.possibleworks.com disable-scheduler
   63  docker exec -it frappe-backend-1 bench --site hris-gvs.possibleworks.com enable-scheduler
   64  docker compose restart frappe-scheduler
   65  find / -name docker-compose.yml 2>/dev/null
   66  cd /root/frappe_docker/devcontainer-example
   67  ls
   68  docker compose restart frappe-scheduler
   69  docker logs frappe-frontend-1 --tail=200
   70  docker restart frappe-backend-1 frappe-frontend-1
   71  docker restart frappe-frontend-1
   72  docker logs frappe-frontend-1 --tail=50
   73  docker exec -it frappe-frontend-1 sh -c "curl -I http://frappe-backend-1:8000"
   74  curl http://frappe-backend-1:8000
   75  dig hris-gvs.possibleworks.com +short
   76  curl http://frappe-backend-1:8000
   77  dig hris-gvs.possibleworks.com +short
   78  docker ps
   79  docker restart frappe-backend-1
   80  docker exec -it frappe-backend-1
   81  docker exec -it frappe-backend-1 bash
   82  docker restart frappe-backend-1
   83  exit
   84  docker exec -it frappe-frontend-1 bash
   85  docker restart frappe-frontend-1
   86  docker exec -it frappe-queue-long-1 bash
   87  docker restart  frappe-queue-long-1
   88  docker exec -it frappe-frontend-1 bash
   89  docker exec -it frappe-queue-long-1 bash
   90  docker exec -it frappe-queue-short-1 bash
   91  docker restart frappe-queue-short-1
   92  exit
   93  docker exec -it frappe-backend-1 bash
   94  docker restart frappe-backend-1
   95  exit
   96  docker info | grep "Docker Root Dir"
   97  ls /var/lib/docker/volumes
   98  history
```
