# categories parser container

### Build image
```
docker build --no-cache ./category/ -t fcmotode-parser-queue/category:latest
```

### Run image
```
docker run -p 9001:9001 -v $(pwd)/app:/app -v $(pwd)/log:/var/log/supervisor -v $(pwd)/log:/var/log/app fcmotode-parser-queue/category:latest
```
