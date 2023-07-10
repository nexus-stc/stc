npm run build-only

API_ADDR=/ip4/0.0.0.0/tcp/5001
CID=$(ipfs --api $API_ADDR add --pin -Q -r --hash=blake3 dist)
ipfs --api $API_ADDR files rm -r /summa-web
ipfs --api $API_ADDR files cp /ipfs/"$CID" /summa-web
ipfs --api $API_ADDR files cp -p /ipfs/bafyb4ics4mkbagdxjjlm5k2styz4wscdbxjpwwojkgrowcdydvs4lnaj3e /summa-web/data/nexus_free
ipfs --api $API_ADDR files cp -p /ipfs/bafyb4if3exj3o2u3sm2s4xvbeu7fkpwm62g7euuzwlfffvq6nbbwueeloq /summa-web/data/nexus_media
ipfs --api $API_ADDR files cp -p /ipfs/bafyb4ibo4h574kj6khe2twsfmo2azxwo77ysc4pxjmh5deup6rntxtlcra /summa-web/data/nexus_science
ipfs --api $API_ADDR files stat --hash /summa-web
