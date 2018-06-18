# fcmotode-parser-queue

### environment variables
```
cp env-example .env
source .env
```

### docker machine & docker swarm
```
docker-machine create -d generic --generic-ip-address 192.168.99.100 --generic-ssh-key ~/.ssh/id_rsa --generic-ssh-user docker fcmoto # change default image (Boot2Docker, RancherOS)
docker swarm init --advertise-addr 192.168.99.100
docker stack deploy -c docker-stack.yml fcmoto
docker stack rm fcmoto
```