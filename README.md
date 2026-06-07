# DoH RFC8484 Batch Resolver

A lightweight Python script that resolves domain names via **DNS-over-HTTPS (DoH)** as defined in **[RFC 8484](https://datatracker.ietf.org/doc/html/rfc8484)**, with multi-server failover and IPv4/IPv6 preference control.

## Features

- **RFC 8484 compliant** — uses `application/dns-message` media type over HTTP POST with raw DNS wire format
- **Multi-server failover** — if the first DoH server fails, falls back to the next
- **IPv4/IPv6 selection** — auto (prefer IPv4, fallback to IPv6), `-4` (IPv4 only), `-6` (IPv6 only)
- **Zero dependencies** — built on Python 3 standard library only (`urllib`, `struct`, `socket`, `ssl`)
- **Batch resolution** — resolves all domains in `domain.ini` in a single run
- **Timestamped output** — results saved to `IP_<YYYYMMDDHHMMSS>.txt`

## Requirements

- Python 3.6+
- No third-party packages required

## Usage

```
python doh-rfc8484-resolver.py [-4 | -6]
```

## Proxy support
Before executing the script, you can set environment variables to resolve the domain name through a proxy.

For Windows:
```
set https_proxy=http://127.0.0.1:8080
```
For Linux/MacOS:
```
export https_proxy=http://127.0.0.1:8080
```

### Options

| Flag     | Description                              |
|----------|------------------------------------------|
| (none)   | Auto mode: prefer A records, fallback to AAAA |
| `-4`     | Resolve only A records (IPv4)            |
| `-6`     | Resolve only AAAA records (IPv6)         |

## Configuration

### `domain.ini`

One domain per line:

```
www.example.com
www.example.net
```

### `dns.ini`

One DoH server URL per line. Servers are tried in order; if one fails, the next is used.

```
https://dns.alidns.com/dns-query
https://doh.pub/dns-query
```

## Output

Results are written to `IP_<YYYYMMDDHHMMSS>.txt`:

```
www.example.com
  A: 104.20.23.154
  A: 172.66.147.243

www.example.net
  AAAA: 2606:4700:10::6814:1508
```

## How It Works

1. Reads domains from `domain.ini`
2. Reads DoH server URLs from `dns.ini`
3. For each domain, builds a DNS query in wire format (RFC 1035) with DNS ID=0 (per RFC 8484 Section 4.1 recommendation for HTTP cache friendliness)
4. Sends an HTTP POST request with `Content-Type: application/dns-message` and `Accept: application/dns-message`
5. Parses the binary DNS response, extracting A (IPv4) and AAAA (IPv6) records
6. If a server fails (timeout, connection error, or HTTP error), tries the next configured server
7. Writes results to a timestamped output file

## References

- [RFC 8484 — DNS Queries over HTTPS (DoH)](https://datatracker.ietf.org/doc/html/rfc8484)
- [RFC 1035 — Domain Names - Implementation and Specification](https://datatracker.ietf.org/doc/html/rfc1035)

## License

GPL 3.0

## Thanks
DeepSeek V4 Flash
