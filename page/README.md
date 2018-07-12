# pages parser container

### Build image
```
docker build --no-cache ./page/ -t fcmotode/page:latest
```

### Push to docker hub
```
docker login # if not logged in yet
docker push fcmotode/page:latest
```

### Run image
```
docker run -p 9001:9001 -v $(pwd)/app:/app -v /var/log:/var/log/supervisor -v /var/log:/var/log/app fcmotode/page:latest
```
