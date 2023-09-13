import { utils } from 'summa-wasm'

async function get_default_cover() {
  const default_cover = await fetch('./default-cover.jpg')
  const blob = await default_cover.blob()
  return URL.createObjectURL(blob);
}
export const default_cover = await get_default_cover()

export function format_bytes (bytes: number, decimals = 2) {
  if (!+bytes) return '0&nbsp;Bytes'

  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']

  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))}&nbsp;${sizes[i]}`
}

export function format_date (unixtime: bigint): string {
  const date = new Date(Number.parseInt(unixtime.toString()) * 1000)
  let month = (date.getMonth() + 1).toString()
  if (month.length < 2) {
    month = '0' + month
  }
  let day = date.getDate().toString()
  if (day.length < 2) {
    day = '0' + day
  }
  return `${date.getFullYear()}-${month}-${day}`
}

export function format_percent (v: number): string {
  return (v * 100).toFixed(2) + '%'
}
export const sleep = async (ms: number) => await new Promise((r) => setTimeout(r, ms))
export function cid_local_link (cid: string, filename: string) {
  const { ipfs_hostname, ipfs_http_protocol } = utils.get_ipfs_hostname()
  return {
    url: `${ipfs_http_protocol}//${ipfs_hostname}/ipfs/${cid}?filename=${filename}`,
    name: 'Local IPFS'
  }
}
export function generate_cid_external_links (cid: string, filename: string) {
  return [
    cid_local_link(cid, filename),
    {
      url: `https://${cid}.ipfs.w3s.link/?filename=${filename}`,
      name: 'Web3 Storage'
    },
    {
      url: `https://crustwebsites.net/ipfs/${cid}?filename=${filename}`,
      name: 'Crust'
    },
    {
      url: `https://cloudflare-ipfs.com/ipfs/${cid}?filename=${filename}`,
      name: 'CloudFlare IPFS'
    },
    {
      url: `https://gateway.pinata.cloud/ipfs/${cid}?filename=${filename}`,
      name: 'Pinata'
    },
    {
      url: `https://ipfs.io/ipfs/${cid}?filename=${filename}`,
      name: 'IPFS.io'
    }
  ]
}
export function generate_filename (title: string) {
  return (
      (title || "unnamed")
      .toLowerCase()
      .replace(/[^\p{L}\p{N}]/gu, ' ')
      .replace(/\s+/gu, ' ')
      .replace(/\s/gu, '-')
  )
}

export function is_int (s: string) {
  return !isNaN(parseFloat(s))
}

export function average (arr: number[]) {
  if (arr.length === 0) {
    return undefined
  }
  let total = 0
  for (let i = 0; i < arr.length; i++) {
    total += arr[i]
  }
  return total / arr.length
}

export function decode_html(html) {
    const txt = document.createElement('textarea');
    txt.innerHTML = html;
    return txt.value;
}

export function remove_unpaired_escaped_tags(str) {
    const openTags = [];
    const regex = /&lt;\/?([a-z][a-z0-9]*)\b[^&]*&gt;/gi;

    // First pass: Handle and remove unpaired closing tags
    let intermediateStr = str.replace(regex, (match, p1) => {
        if (match.startsWith('&lt;/')) {
            if (openTags.length && openTags[openTags.length - 1] === p1) {
                openTags.pop();
                return match; // Keep the closing tag if it matches the last opening tag
            }
            return ''; // Remove the closing tag if it doesn't match the last opening tag
        } else {
            openTags.push(p1);
            return match; // Keep the opening tag for now
        }
    });

    // Second pass: Remove unpaired opening tags
    for (const tag of openTags) {
        const unpairedTag = new RegExp(`&lt;${tag}\\b[^&]*&gt;`, 'gi');
        intermediateStr = intermediateStr.replace(unpairedTag, '');
    }

    return intermediateStr;
}

