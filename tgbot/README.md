### Launching bots

- The first startup will be slow!
- Make sure to mount volumes for persistence. Otherwise, after every restart, you will lose your caches and databases (including users and riot bots).
- Beforehand, you need to set up all credentials in the `.env.light` file. After setting them up, execute the following command in the Terminal:

```bash
docker compose --env-file .env.light up --force-recreate --build
```
Wait for the following line to be displayed in the logs:
```bash
light-tgbot-1  | INFO:statbox:{'action': 'started', 'mode': 'dynamic_bot', 'bot_name': '<bot_name>'}
```

Possible performance optimizations, from least to most complicated:

- Mount to tgbot to cache bot credentials:
    ```yaml
    volumes:
    - /usr/lib/stc-tgbot:/usr/lib/stc-tgbot
    - /var/log/stc-tgbot:/var/log/stc-tgbot
    ```
- Mount to ipfs to cache the database and downloaded items:
    ```yaml
    volumes:
    - /data/ipfs:/data/ipfs
    ```
- If you have mounted volumes to ipfs, pin the database to IPFS:
    ```bash
    docker compose --env-file .env.light exec ipfs ipfs pin add /ipns/standard-template-construct.org --progress
    ```
- Host the database directly (requires development experience).