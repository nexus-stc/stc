npm run build-only

API_ADDR=($(jq -r '.ipfs_api_multiaddr' summa-config.json))
DIST_CID=$(ipfs --api $API_ADDR add --pin -Q -r --hash=blake3 dist)
ipfs --api $API_ADDR files rm -r /stc-web
ipfs --api $API_ADDR files cp /ipfs/"$DIST_CID" /stc-web
jq -r -c '.indices | keys[]' summa-config.json | while read INDEX_NAME; do
  INDEX_CID=$(jq -r -c ".indices.$INDEX_NAME" summa-config.json)
  ipfs --api $API_ADDR files cp -p /ipfs/$INDEX_CID /stc-web/data/$INDEX_NAME
done
ipfs --api $API_ADDR files stat --hash /stc-web
