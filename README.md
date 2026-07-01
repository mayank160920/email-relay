# Email Relay

A simple catch-all email forwarder. Receives all emails sent to your domain (and subdomains) and forwards them directly to your Gmail inbox via Gmail's MX servers.

No third-party email services required — just a VPS with outbound port 25 open.

## How It Works

```
[Sender] --SMTP port 25--> [Your VPS: relay.py] --SMTP port 25--> [Gmail MX] --> [Your Gmail Inbox]
```

1. DNS MX records point your domain to your VPS
2. The script accepts all incoming emails (any address, any subdomain)
3. It resolves Gmail's MX records and delivers the email directly
4. Original sender headers are preserved — Gmail shows who actually sent the email

## Quick Start

### 1. Configure

Edit `config.py`:

```python
GMAIL_ADDRESS = "you@gmail.com"        # Your Gmail address
FORWARD_DOMAIN = "yourdomain.com"      # Your domain
ENVELOPE_SENDER = "relay@yourdomain.com"  # Envelope sender (for SPF)
```

Or use environment variables (useful with Docker):

```bash
export RELAY_GMAIL_ADDRESS="you@gmail.com"
export RELAY_FORWARD_DOMAIN="yourdomain.com"
export RELAY_ENVELOPE_SENDER="relay@yourdomain.com"
export RELAY_LISTEN_PORT="25"
export RELAY_SMTP_TIMEOUT="30"
```

Environment variables override values in `config.py`.

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run

```bash
sudo python3 relay.py
```

Port 25 requires root. To avoid running as root:

```bash
# Grant the Python binary permission to bind low ports
sudo setcap cap_net_bind_service=+ep $(which python3)
python3 relay.py
```

### 4. Run with Docker (Alternative)

```bash
# Build the image
docker build -t email-relay .

# Run with environment variables
docker run -d \
  --name email-relay \
  -p 25:25 \
  -e RELAY_GMAIL_ADDRESS="you@gmail.com" \
  -e RELAY_FORWARD_DOMAIN="yourdomain.com" \
  --restart unless-stopped \
  email-relay
```

Docker handles port binding and auto-restart for you.

## DNS Setup

Add these records at your domain registrar / DNS provider:

### MX Records (Required)

| Type | Name | Value | Priority |
|------|------|-------|----------|
| MX | `yourdomain.com` | `<VPS_IP>` | 10 |
| MX | `*.yourdomain.com` | `<VPS_IP>` | 10 |

The wildcard MX record ensures emails to `anything@sub.yourdomain.com` are also caught.

**Note:** Some DNS providers require a hostname instead of a raw IP for MX records. In that case, create an A record first:

| Type | Name | Value |
|------|------|-------|
| A | `mail.yourdomain.com` | `<VPS_IP>` |

Then point your MX records to `mail.yourdomain.com` instead of the IP.

### SPF Record (Required for Deliverability)

| Type | Name | Value |
|------|------|-------|
| TXT | `yourdomain.com` | `v=spf1 ip4:<VPS_IP> -all` |

This tells Gmail that your VPS is authorized to send email on behalf of your domain.

### Reverse DNS / PTR Record (Recommended)

Set the PTR record for your VPS IP to point to `mail.yourdomain.com` (or your domain). This is configured in your VPS provider's control panel, **not** in your domain's DNS.

Gmail is more likely to accept email from IPs with valid reverse DNS.

## VPS Setup

### Requirements

- A VPS with **outbound port 25 open** (see provider notes below)
- Inbound port 25 open in the firewall
- Python 3.8+
- No other service running on port 25

### Firewall

Ensure port 25 is open for inbound TCP traffic:

```bash
# UFW (Ubuntu/Debian)
sudo ufw allow 25/tcp

# firewalld (CentOS/RHEL)
sudo firewall-cmd --permanent --add-port=25/tcp
sudo firewall-cmd --reload

# iptables
sudo iptables -A INPUT -p tcp --dport 25 -j ACCEPT
```

### Installation

```bash
# Install Python and pip (Ubuntu/Debian)
sudo apt update && sudo apt install -y python3 python3-pip

# Clone or copy the project
cd /opt
git clone <your-repo-url> email-relay
cd email-relay

# Install dependencies
pip install -r requirements.txt

# Run
sudo python3 relay.py
```

### Running in Background

```bash
# Simple background with nohup
nohup sudo python3 relay.py &

# Or with screen
screen -S relay
sudo python3 relay.py
# Ctrl+A, D to detach
```

## Verification

### 1. Check DNS Propagation

```bash
dig MX yourdomain.com
# Should show your VPS IP with priority 10

dig TXT yourdomain.com
# Should show your SPF record
```

### 2. Test Outbound Port 25

From your VPS:

```bash
telnet gmail-smtp-in.l.google.com 25
# Should connect and show a 220 greeting
# Type QUIT to exit
# or
timeout 5 bash -c '</dev/tcp/gmail-smtp-in.l.google.com/25' && echo "Port 25 reachable" || echo "Blocked"
```

If this times out, your provider blocks outbound port 25.

### 3. Test the Relay

From your VPS (install swaks: `sudo apt install swaks`):

```bash
swaks --to test@yourdomain.com --from sender@example.com --server localhost
```

Or send a real email from any external email account to `anything@yourdomain.com` and check your Gmail.

## VPS Provider Notes

| Provider | Port 25 Status |
|----------|---------------|
| **Hetzner** | Generally open. May be blocked for first ~30 days on new accounts. Contact support to unblock. |
| **OVH / OVHcloud** | Open by default. Strict abuse monitoring. |
| **Vultr** | Blocked on some plans/regions. Submit support ticket to unblock. |
| **DigitalOcean** | Blocked by default. Submit support ticket to unblock. |
| **Kamatera** | Usually open immediately, even on free trial. |
| **AWS / GCP / Azure** | Blocked by default. Requires approval process (not recommended for this use case). |

**Before purchasing a VPS**, verify port 25 is open by checking the provider's docs or contacting their support.

## Deliverability Tips

1. **SPF record is essential** — without it, Gmail will likely reject or spam-folder your forwarded emails
2. **PTR record helps** — set reverse DNS to match your domain
3. **Don't use a fresh IP for high volume** — warm up gradually if sending many emails
4. **Check spam folder initially** — first few emails may land in spam until Gmail learns to trust your IP
5. **DKIM is optional for forwarding** — since you're preserving the original message, the original sender's DKIM signature may still validate (if they signed it)

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Script says "Address already in use" | Another service (postfix, sendmail) is on port 25. Stop it: `sudo systemctl stop postfix` |
| Emails land in Gmail spam | Check SPF record, set PTR record, check IP reputation at [multirbl.valli.org](http://multirbl.valli.org/) |
| "Connection timed out" on forward | Outbound port 25 is blocked. Contact VPS provider. |
| Gmail rejects with 550 | Your IP may be blacklisted. Check [mxtoolbox.com/blacklists](https://mxtoolbox.com/blacklists.aspx) |
| No emails arriving at all | Verify MX records with `dig MX yourdomain.com`, ensure DNS has propagated |

## License

MIT
