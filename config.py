"""
Email Relay Configuration.

Edit the values below, or override them with environment variables.
"""

import os

# Your Gmail address where all emails will be forwarded
GMAIL_ADDRESS = os.environ.get("RELAY_GMAIL_ADDRESS", "you@gmail.com")

# Your domain (used as envelope sender for SPF alignment)
FORWARD_DOMAIN = os.environ.get("RELAY_FORWARD_DOMAIN", "yourdomain.com")

# Envelope sender address (MAIL FROM) - should be on your domain
ENVELOPE_SENDER = os.environ.get("RELAY_ENVELOPE_SENDER", f"relay@{FORWARD_DOMAIN}")

# SMTP server listen settings
LISTEN_HOST = os.environ.get("RELAY_LISTEN_HOST", "0.0.0.0")
LISTEN_PORT = int(os.environ.get("RELAY_LISTEN_PORT", "25"))

# Connection timeout for outbound SMTP (seconds)
SMTP_TIMEOUT = int(os.environ.get("RELAY_SMTP_TIMEOUT", "30"))
