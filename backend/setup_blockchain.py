"""
One-click local blockchain setup for Crop Insurance.

Usage:
    python setup_blockchain.py
"""

from __future__ import annotations

import json
from pathlib import Path

from web3 import Web3

from deploy_contract import deploy_contract
from services.blockchain_service import BlockchainService

GANACHE_URL = "http://127.0.0.1:7545"
BASE_DIR = Path(__file__).resolve().parent
CONTRACTS_DIR = BASE_DIR / "contracts"
ADDRESS_FILE = CONTRACTS_DIR / "deployed_address.json"
ABI_FILE = CONTRACTS_DIR / "CropInsurance.json"


def check_ganache() -> Web3:
    web3 = Web3(Web3.HTTPProvider(GANACHE_URL))
    if not web3.is_connected():
        raise RuntimeError(
            "Ganache is not running at http://127.0.0.1:7545. "
            "Open Ganache GUI and click 'Quickstart Ethereum'."
        )
    return web3


def print_header() -> None:
    print("=" * 64)
    print("Crop Insurance - Local Blockchain Setup")
    print("=" * 64)


def test_contract() -> None:
    service = BlockchainService()

    if service.simulation_mode:
        raise RuntimeError(
            "BlockchainService is still in simulation mode after deployment. "
            "Please verify Ganache is running and artifacts exist in backend/contracts."
        )

    if not service.web3:
        raise RuntimeError("Web3 client is unavailable after setup.")

    owner = service.account
    farmer = service.web3.eth.accounts[1] if len(service.web3.eth.accounts) > 1 else owner

    policy_id = "POL-SETUP-001"
    claim_id = "CLM-SETUP-001"

    premium_wei = service.web3.to_wei(0.01, "ether")
    coverage_wei = service.web3.to_wei(0.05, "ether")

    print("\nRunning post-deployment test transactions...")

    create_result = service.create_policy_on_chain(
        policy_id=policy_id,
        farmer=farmer,
        premium_wei=int(premium_wei),
        coverage_wei=int(coverage_wei),
        crop_type="wheat",
    )
    if not create_result.get("success"):
        raise RuntimeError(f"create_policy_on_chain failed: {create_result}")

    pay_result = service.pay_premium_on_chain(
        policy_id=policy_id,
        from_address=farmer,
        amount_wei=int(premium_wei),
    )
    if not pay_result.get("success"):
        raise RuntimeError(f"pay_premium_on_chain failed: {pay_result}")

    # Weather + NDVI both true => approved payout
    process_result = service.process_claim_on_chain(
        claim_id=claim_id,
        policy_id=policy_id,
        weather_trigger=True,
        ndvi_trigger=True,
        payout_amount_wei=int(service.web3.to_wei(0.005, "ether")),
    )
    if not process_result.get("success"):
        raise RuntimeError(f"process_claim_on_chain failed: {process_result}")

    policy_result = service.get_policy_from_chain(policy_id)
    if not policy_result.get("success"):
        raise RuntimeError(f"get_policy_from_chain failed: {policy_result}")

    claim_result = service.get_claim_from_chain(claim_id)
    if not claim_result.get("success"):
        raise RuntimeError(f"get_claim_from_chain failed: {claim_result}")

    print("Test policy and claim created successfully.")
    print(json.dumps({
        "policy": policy_result["policy"],
        "claim": claim_result["claim"],
    }, indent=2))


def print_next_steps() -> None:
    print("\n" + "-" * 64)
    print("Setup completed.")
    print("-" * 64)
    print("Artifacts generated:")
    print(f"  ABI: {ABI_FILE}")
    print(f"  Address: {ADDRESS_FILE}")
    print("\nNext steps:")
    print("  1. Keep Ganache running.")
    print("  2. Start backend: python app.py")
    print("  3. Use frontend to create policies and process claims.")


def main() -> int:
    print_header()

    try:
        web3 = check_ganache()
        print("Ganache connected.")
        print(f"  Chain ID: {web3.eth.chain_id}")
        print(f"  Accounts: {len(web3.eth.accounts)}")

        address = deploy_contract()
        print(f"Contract deployed at: {address}")

        test_contract()
        print_next_steps()
        return 0
    except Exception as exc:
        print("\nSetup failed.")
        print(f"Reason: {exc}")
        print("\nTroubleshooting:")
        print("  - Ensure Ganache GUI is running at http://127.0.0.1:7545")
        print("  - Install dependencies: pip install py-solc-x web3")
        print("  - Re-run: python setup_blockchain.py")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
