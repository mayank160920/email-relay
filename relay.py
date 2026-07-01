#!/usr/bin/env python3
"""
Email Relay - Catch-all email forwarder to Gmail via direct MX delivery.

Receives all emails on port 25 and forwards them directly to Gmail's MX servers.
No intermediary services required - just a VPS with outbound port 25 open.
"""

import asyncio
import smtplib
import sys
from datetime import datetime, timezone
from email import message_from_bytes

import dns.resolver
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import Envelope

from config import (
    ENVELOPE_SENDER,
    FORWARD_DOMAIN,
    GMAIL_ADDRESS,
    LISTEN_HOST,
    LISTEN_PORT,
    SMTP_TIMEOUT,
)


def log(message: str) -> None:
    """Print a timestamped message to stderr."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{timestamp}] {message}", file=sys.stderr, flush=True)


def resolve_gmail_mx() -> list[str]:
    """Resolve Gmail's MX records, sorted by priority (lowest first)."""
    try:
        answers = dns.resolver.resolve("gmail.com", "MX")
        mx_records = sorted(answers, key=lambda r: r.preference)
        return [str(r.exchange).rstrip(".") for r in mx_records]
    except dns.resolver.DNSException as e:
        log(f"ERROR: Failed to resolve Gmail MX records: {e}")
        return []


def forward_to_gmail(envelope: Envelope) -> bool:
    """
    Forward an email directly to Gmail's MX servers.

    Returns True if delivery succeeded, False otherwise.
    """
    mx_hosts = resolve_gmail_mx()
    if not mx_hosts:
        log("ERROR: No Gmail MX records found, cannot forward")
        return False

    # Parse the original message and add X-Original-To header
    original_msg = message_from_bytes(envelope.content)
    original_recipients = ", ".join(envelope.rcpt_tos)
    original_msg["X-Original-To"] = original_recipients

    # Convert back to bytes for sending
    msg_data = original_msg.as_bytes()

    # Try each MX host in priority order
    for mx_host in mx_hosts:
        try:
            with smtplib.SMTP(mx_host, 25, timeout=SMTP_TIMEOUT) as smtp:
                smtp.ehlo(FORWARD_DOMAIN)
                smtp.sendmail(ENVELOPE_SENDER, [GMAIL_ADDRESS], msg_data)
            log(f"OK: Forwarded to {GMAIL_ADDRESS} via {mx_host} "
                f"(from: {envelope.mail_from}, to: {original_recipients})")
            return True
        except smtplib.SMTPException as e:
            log(f"WARN: Failed to deliver via {mx_host}: {e}")
            continue
        except (OSError, TimeoutError) as e:
            log(f"WARN: Connection failed to {mx_host}: {e}")
            continue

    log(f"ERROR: All MX hosts failed for message from {envelope.mail_from}")
    return False


class CatchAllHandler:
    """SMTP handler that accepts all emails and forwards them to Gmail."""

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        """Accept all recipients (catch-all)."""
        envelope.rcpt_tos.append(address)
        return "250 OK"

    async def handle_DATA(self, server, session, envelope):
        """Receive email data and forward to Gmail."""
        # Parse for logging
        msg = message_from_bytes(envelope.content)
        subject = msg.get("Subject", "(no subject)")
        sender = envelope.mail_from
        recipients = ", ".join(envelope.rcpt_tos)

        log(f"RECV: from={sender} to={recipients} subject={subject}")

        # Forward in a thread to avoid blocking the async loop
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(None, forward_to_gmail, envelope)

        if success:
            return "250 Message accepted for delivery"
        else:
            return "451 Temporary failure, please retry later"


def main():
    """Start the SMTP relay server."""
    handler = CatchAllHandler()
    controller = Controller(
        handler,
        hostname=LISTEN_HOST,
        port=LISTEN_PORT,
    )

    log(f"Starting email relay on {LISTEN_HOST}:{LISTEN_PORT}")
    log(f"Forwarding all mail to: {GMAIL_ADDRESS}")
    log(f"Envelope sender: {ENVELOPE_SENDER}")
    log(f"Press Ctrl+C to stop")

    controller.start()

    try:
        # Keep the main thread alive
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_forever()
    except KeyboardInterrupt:
        log("Shutting down...")
    finally:
        controller.stop()


if __name__ == "__main__":
    main()
