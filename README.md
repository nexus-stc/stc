# STC Repository

### Launching bots

You need to set up all credentials in `.env.light` file beforehand. After setting,
execute the following in the Terminal:

```bash
docker compose --env-file .env.light up --force-recreate --build
```

Possible performance optimizations, from less to more complicated
- mount to tgbot-light, it caches bot credentials
    ```yaml
    volumes:
    - /usr/lib/stc-tgbot:/usr/lib/stc-tgbot
    - /var/log/stc-tgbot:/var/log/stc-tgbot
    ```
- mount to ipfs-light, it caches database and downloaded items
    ```yaml
    volumes:
    - /data/ipfs:/data/ipfs
    ```
- pin database to IPFS (only if you mounted volumes to light-ipfs)
    ```bash
    docker compose --env-file .env.light exec ipfs-light ipfs pin add /ipns/standard-template-construct.org --progress
    ```
- host database directly, development experience required