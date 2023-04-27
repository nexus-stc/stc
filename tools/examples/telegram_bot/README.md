## How to launch

- Install [IPFS](https://docs.ipfs.tech/install/ipfs-desktop/) and Python3
- `git clone git@github.com:nexus-stc/stc.git && cd stc/tools/examples/telegram_bot`
- Setup environment:
```bash 
python3 -m venv venv && source venv/bin/activate && pip3 install -r requirements.txt
```
- Retrieve your own credentials from https://my.telegram.org and @BotFather
- Launch bot:
Bot may be launched in the following way then:
```bash
API_ID=... API_HASH=... BOT_TOKEN=... python main.py
```