"""x402Escrow / EIP-3009 signing helper for the platform wallet.

Used by the MCP path of FortytwoPrimeProvider. Signs a USDC
ReceiveWithAuthorization typed-data payload against the Fortytwo escrow
recipient and returns the base64-encoded payload that goes in the
`payment-signature` HTTP header.

References (sourced from official Fortytwo docs):
- USDC EIP-712 domain: name="USD Coin", version="2", chainId=<chain>, verifyingContract=USDC.
- Type: ReceiveWithAuthorization {from, to, value, validAfter, validBefore, nonce}.
- USDC contract on Monad mainnet: 0x754704Bc059F8C67012fEd69BC8A327a5aafb603.
- USDC contract on Base mainnet:  0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913.
- Fortytwo escrow recipient:      0x9562f50f73d8ee22276f13a18d051456d8d137a0.
"""

from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass

from eth_account import Account
from eth_account.messages import encode_typed_data

from app.config import get_settings
from app.logging import get_logger

log = get_logger(__name__)


CHAIN_IDS = {"monad": 143, "base": 8453}


def _checksum(address: str) -> str:
    """Cheap checksum: rely on eth_account when needed; here we just lower-case."""
    return address.lower() if address.startswith("0x") else "0x" + address.lower()


@dataclass(frozen=True)
class PaymentAuthorization:
    """The raw payment-signature payload (pre-base64). Mirrors the docs' field names."""

    client: str          # platform wallet address (signer)
    to: str              # escrow recipient
    value: int           # amount in USDC base units
    valid_after: int     # unix seconds
    valid_before: int    # unix seconds
    nonce_hex: str       # 0x-prefixed 32-byte hex
    v: int
    r_hex: str           # 0x-prefixed 32-byte hex
    s_hex: str           # 0x-prefixed 32-byte hex
    chain_id: int
    usdc_address: str

    def to_header_payload(self, max_amount: int) -> dict:
        """Serialize into the JSON the `payment-signature` header carries.

        The official docs spell this out as `{client, maxAmount, validAfter,
        validBefore, nonce, v, r, s}`. We add `chainId` and `verifyingContract`
        defensively — they let the server route across multiple chains without
        guessing.
        """
        return {
            "client": self.client,
            "to": self.to,
            "maxAmount": str(max_amount),
            "value": str(self.value),
            "validAfter": str(self.valid_after),
            "validBefore": str(self.valid_before),
            "nonce": self.nonce_hex,
            "v": self.v,
            "r": self.r_hex,
            "s": self.s_hex,
            "chainId": self.chain_id,
            "verifyingContract": self.usdc_address,
        }


class WalletSigner:
    """Reads the platform wallet from settings and signs EIP-3009 authorizations."""

    def __init__(self) -> None:
        s = get_settings()
        if not s.platform_wallet_private_key:
            raise RuntimeError("PLATFORM_WALLET_PRIVATE_KEY is not set")
        if s.platform_wallet_chain not in CHAIN_IDS:
            raise RuntimeError(
                f"unsupported platform_wallet_chain={s.platform_wallet_chain!r}; "
                f"expected one of {list(CHAIN_IDS)}"
            )
        pk = s.platform_wallet_private_key
        if not pk.startswith(("0x", "0X")):
            pk = "0x" + pk
        self._account = Account.from_key(pk)
        self._chain = s.platform_wallet_chain
        self._chain_id = CHAIN_IDS[self._chain]
        self._usdc = (
            s.usdc_monad_address if self._chain == "monad" else s.usdc_base_address
        )
        self._escrow = s.fortytwo_escrow_recipient
        self._max_amount = s.fortytwo_max_payment_usdc_units

    @property
    def address(self) -> str:
        return self._account.address

    @property
    def chain(self) -> str:
        return self._chain

    @property
    def chain_id(self) -> int:
        return self._chain_id

    @property
    def usdc_address(self) -> str:
        return self._usdc

    @property
    def escrow_recipient(self) -> str:
        return self._escrow

    @property
    def max_amount(self) -> int:
        return self._max_amount

    def sign_authorization(
        self,
        *,
        amount: int | None = None,
        valid_seconds: int = 600,
    ) -> PaymentAuthorization:
        """Sign a USDC ReceiveWithAuthorization payload for `amount` (default = max)."""
        amount = amount or self._max_amount
        now = int(time.time())
        valid_after = now - 5
        valid_before = now + valid_seconds
        nonce = "0x" + os.urandom(32).hex()

        domain = {
            "name": "USD Coin",
            "version": "2",
            "chainId": self._chain_id,
            "verifyingContract": _checksum(self._usdc),
        }
        types = {
            "ReceiveWithAuthorization": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
            ],
        }
        message = {
            "from": self._account.address,
            "to": _checksum(self._escrow),
            "value": amount,
            "validAfter": valid_after,
            "validBefore": valid_before,
            "nonce": nonce,
        }
        full_message = {
            "domain": domain,
            "types": {**types, "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ]},
            "primaryType": "ReceiveWithAuthorization",
            "message": message,
        }
        signable = encode_typed_data(full_message=full_message)
        signed = self._account.sign_message(signable)
        return PaymentAuthorization(
            client=self._account.address,
            to=_checksum(self._escrow),
            value=amount,
            valid_after=valid_after,
            valid_before=valid_before,
            nonce_hex=nonce,
            v=signed.v,
            r_hex=hex(signed.r) if isinstance(signed.r, int) else signed.r.hex(),
            s_hex=hex(signed.s) if isinstance(signed.s, int) else signed.s.hex(),
            chain_id=self._chain_id,
            usdc_address=_checksum(self._usdc),
        )


def encode_payment_signature_header(auth: PaymentAuthorization, max_amount: int) -> str:
    """Encode a PaymentAuthorization for the `payment-signature` header.

    The official docs' phrasing is "Base64-encoded x402 signature". We base64
    the JSON payload of `to_header_payload` so the server can decode and verify.
    """
    body = json.dumps(auth.to_header_payload(max_amount), separators=(",", ":"))
    return base64.b64encode(body.encode("utf-8")).decode("ascii")
