"""
Blockchain Service - Local Ganache + Smart Contract Integration

- Auto-loads deployed address + ABI from backend/contracts
- Falls back to simulation mode if Ganache/contract artifacts are unavailable
"""

from __future__ import annotations

import json
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from web3 import Web3
from config import active_config as config


class BlockchainService:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent
        self.contracts_dir = self.base_dir / "contracts"
        self.abi_path = self.contracts_dir / "CropInsurance.json"
        self.address_path = self.contracts_dir / "deployed_address.json"

        self.web3: Optional[Web3] = None
        self.contract = None
        self.account: Optional[str] = None
        self.connected = False
        self.simulation_mode = True

        self._connect_and_load()

    def _connect_and_load(self) -> None:
        """Connect to Ganache and load deployed contract artifacts."""
        try:
            self.web3 = Web3(Web3.HTTPProvider(config.GANACHE_URL))
            if not self.web3.is_connected():
                print("BlockchainService: Ganache not reachable. Using simulation mode.")
                return

            self.connected = True
            self.simulation_mode = False
            self.account = self.web3.eth.accounts[0]
            self.web3.eth.default_account = self.account

            loaded = self._load_contract_from_files()
            if not loaded:
                print("BlockchainService: Contract artifacts not found/invalid. Using simulation mode.")
                self.simulation_mode = True

            print(f"BlockchainService: Connected={self.connected}, Simulation={self.simulation_mode}")
        except Exception as exc:
            print(f"BlockchainService: connection failed ({exc}). Using simulation mode.")
            self.connected = False
            self.simulation_mode = True

    def _load_contract_from_files(self) -> bool:
        """Load contract ABI + deployed address from backend/contracts."""
        if not self.abi_path.exists() or not self.address_path.exists() or not self.web3:
            return False

        try:
            abi_raw = json.loads(self.abi_path.read_text(encoding="utf-8"))
            if isinstance(abi_raw, dict) and "abi" in abi_raw:
                abi = abi_raw["abi"]
            else:
                abi = abi_raw

            address_data = json.loads(self.address_path.read_text(encoding="utf-8"))
            contract_address = address_data.get("address")
            if not contract_address:
                return False

            self.contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=abi,
            )
            return True
        except Exception as exc:
            print(f"BlockchainService: failed to load contract artifacts ({exc})")
            self.contract = None
            return False

    def get_connection_status(self) -> dict:
        """Get blockchain connectivity + mode status."""
        if not self.connected:
            return {
                "success": False,
                "connected": False,
                "simulation_mode": True,
                "error": "Ganache not connected",
            }

        status = {
            "success": True,
            "connected": True,
            "simulation_mode": self.simulation_mode,
            "network_id": self.web3.eth.chain_id if self.web3 else None,
            "account": self.account,
        }

        if self.web3 and self.account:
            status["balance_eth"] = float(
                self.web3.from_wei(self.web3.eth.get_balance(self.account), "ether")
            )

        return status

    def _ensure_contract_ready(self) -> bool:
        return bool(self.connected and not self.simulation_mode and self.contract and self.web3 and self.account)

    def create_policy_on_chain(
        self,
        policy_id: str,
        farmer: str,
        premium_wei: int,
        coverage_wei: int,
        crop_type: str,
    ) -> dict:
        """Call createPolicy(policyId, farmer, premium, coverage, cropType)."""
        if not self._ensure_contract_ready():
            return self.simulate_transaction(policy_id, payout_eth=0.0, action="create_policy")

        try:
            tx_hash = self.contract.functions.createPolicy(
                policy_id,
                Web3.to_checksum_address(farmer),
                int(premium_wei),
                int(coverage_wei),
                crop_type,
            ).transact({"from": self.account})
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            return {
                "success": True,
                "simulated": False,
                "action": "create_policy",
                "policy_id": policy_id,
                "transaction_hash": tx_hash.hex(),
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as exc:
            return {"success": False, "simulated": False, "error": str(exc)}

    def pay_premium_on_chain(self, policy_id: str, from_address: Optional[str], amount_wei: int) -> dict:
        """Call payPremium(policyId) with payable value."""
        if not self._ensure_contract_ready():
            return self.simulate_transaction(policy_id, payout_eth=0.0, action="pay_premium")

        payer = Web3.to_checksum_address(from_address) if from_address else self.account

        try:
            tx_hash = self.contract.functions.payPremium(policy_id).transact(
                {
                    "from": payer,
                    "value": int(amount_wei),
                }
            )
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            return {
                "success": True,
                "simulated": False,
                "action": "pay_premium",
                "policy_id": policy_id,
                "transaction_hash": tx_hash.hex(),
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed,
                "amount_wei": int(amount_wei),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as exc:
            return {"success": False, "simulated": False, "error": str(exc)}

    def process_claim_on_chain(
        self,
        claim_id: str,
        policy_id: str,
        weather_trigger: bool,
        ndvi_trigger: bool,
        payout_amount_wei: int,
    ) -> dict:
        """Call processClaim(claimId, policyId, weatherTrigger, ndviTrigger, payoutAmount)."""
        if not self._ensure_contract_ready():
            return self.simulate_transaction(
                policy_id,
                payout_eth=float(payout_amount_wei) / 10**18,
                action="process_claim",
                extra={
                    "claim_id": claim_id,
                    "weather_trigger": weather_trigger,
                    "ndvi_trigger": ndvi_trigger,
                    "approved": bool(weather_trigger and ndvi_trigger),
                },
            )

        try:
            tx_hash = self.contract.functions.processClaim(
                claim_id,
                policy_id,
                bool(weather_trigger),
                bool(ndvi_trigger),
                int(payout_amount_wei),
            ).transact({"from": self.account})
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            return {
                "success": True,
                "simulated": False,
                "action": "process_claim",
                "claim_id": claim_id,
                "policy_id": policy_id,
                "approved": bool(weather_trigger and ndvi_trigger),
                "transaction_hash": tx_hash.hex(),
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as exc:
            return {"success": False, "simulated": False, "error": str(exc)}

    def get_policy_from_chain(self, policy_id: str) -> dict:
        """Call getPolicy(policyId) view function."""
        if not self._ensure_contract_ready():
            return {
                "success": False,
                "simulated": True,
                "error": "Contract not ready; running in simulation mode.",
            }

        try:
            raw = self.contract.functions.getPolicy(policy_id).call()
            return {
                "success": True,
                "simulated": False,
                "policy": {
                    "policy_id": raw[0],
                    "farmer": raw[1],
                    "premium_wei": int(raw[2]),
                    "coverage_wei": int(raw[3]),
                    "crop_type": raw[4],
                    "premium_paid": bool(raw[5]),
                    "active": bool(raw[6]),
                    "claimed": bool(raw[7]),
                    "created_at": int(raw[8]),
                },
            }
        except Exception as exc:
            return {"success": False, "simulated": False, "error": str(exc)}

    def get_claim_from_chain(self, claim_id: str) -> dict:
        """Call getClaim(claimId) view function."""
        if not self._ensure_contract_ready():
            return {
                "success": False,
                "simulated": True,
                "error": "Contract not ready; running in simulation mode.",
            }

        try:
            raw = self.contract.functions.getClaim(claim_id).call()
            return {
                "success": True,
                "simulated": False,
                "claim": {
                    "claim_id": raw[0],
                    "policy_id": raw[1],
                    "weather_trigger": bool(raw[2]),
                    "ndvi_trigger": bool(raw[3]),
                    "approved": bool(raw[4]),
                    "payout_amount_wei": int(raw[5]),
                    "processed_at": int(raw[6]),
                },
            }
        except Exception as exc:
            return {"success": False, "simulated": False, "error": str(exc)}

    # ---------------------------------------------------------------------
    # Backward-compatible wrappers used by existing backend app.py
    # ---------------------------------------------------------------------

    def create_policy(
        self,
        farmer_address: str,
        policy_id: str,
        premium_wei: int,
        coverage_wei: int,
        lat: int,
        lon: int,
        crop_type: str,
    ) -> dict:
        return self.create_policy_on_chain(
            policy_id=policy_id,
            farmer=farmer_address,
            premium_wei=premium_wei,
            coverage_wei=coverage_wei,
            crop_type=crop_type,
        )

    def pay_premium(self, policy_id: str, amount_wei: int, from_address: str) -> dict:
        return self.pay_premium_on_chain(policy_id=policy_id, from_address=from_address, amount_wei=amount_wei)

    def trigger_payout(
        self,
        policy_id: str,
        weather_trigger: bool,
        ndvi_trigger: bool,
        payout_amount_wei: int,
    ) -> dict:
        claim_id = f"CLM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        return self.process_claim_on_chain(
            claim_id=claim_id,
            policy_id=policy_id,
            weather_trigger=weather_trigger,
            ndvi_trigger=ndvi_trigger,
            payout_amount_wei=payout_amount_wei,
        )

    def get_policy(self, policy_id: str) -> dict:
        return self.get_policy_from_chain(policy_id)

    def simulate_transaction(
        self,
        policy_id: str,
        payout_eth: float,
        action: str = "simulate",
        extra: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """Generate a deterministic-style simulated transaction result."""
        payload = f"{action}-{policy_id}-{payout_eth}-{time.time()}"
        tx_hash = "0x" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

        data = {
            "success": True,
            "simulated": True,
            "action": action,
            "policy_id": policy_id,
            "transaction_hash": tx_hash,
            "block_number": 0,
            "gas_used": 21000,
            "payout_amount_eth": payout_eth,
            "timestamp": datetime.now().isoformat(),
            "note": "Ganache/contract not available; using simulation mode.",
        }
        if extra:
            data.update(extra)
        return data


if __name__ == "__main__":
    service = BlockchainService()
    print(json.dumps(service.get_connection_status(), indent=2))
