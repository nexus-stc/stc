npm run build-only

API_ADDR=($(jq -r '.ipfs_api_multiaddr' summa-config.json))
echo Adding dist...
DIST_CID=$(ipfs --api $API_ADDR add --pin -Q -r --hash=blake3 dist)
echo Settings MFS...
ipfs --api $API_ADDR files rm -r /stc-web
ipfs --api $API_ADDR files cp /ipfs/"$DIST_CID" /stc-web
INDEX_CID=$(jq -r -c '.index' summa-config.json)
ipfs --api $API_ADDR files cp -p /ipfs/$INDEX_CID /stc-web/data
ipfs --api $API_ADDR files cp -p /ipfs/bafybeiaysi4s6lnjev27ln5icwm6tueaw2vdykrtjkwiphwekaywqhcjze/I /stc-web/images/wiki
ipfs --api $API_ADDR files stat --hash /stc-web
