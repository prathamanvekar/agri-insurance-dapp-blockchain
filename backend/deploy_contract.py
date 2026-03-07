"""
Deploy CropInsurance contract to local Ganache.

Usage:
    python deploy_contract.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Tuple

from solcx import compile_standard, install_solc
from web3 import Web3

GANACHE_URL = "http://127.0.0.1:7545"
SOLC_VERSION = "0.8.19"

BASE_DIR = Path(__file__).resolve().parent
CONTRACTS_DIR = BASE_DIR / "contracts"
SOL_FILE = CONTRACTS_DIR / "CropInsurance.sol"
ABI_FILE = CONTRACTS_DIR / "CropInsurance.json"
ADDRESS_FILE = CONTRACTS_DIR / "deployed_address.json"
CONFIG_FILE = BASE_DIR / "config.py"


def _connect_web3() -> Web3:
    web3 = Web3(Web3.HTTPProvider(GANACHE_URL))
    if not web3.is_connected():
        raise RuntimeError(
            "Could not connect to Ganache at http://127.0.0.1:7545. "
            "Please open Ganache and start Quickstart Ethereum."
        )
    return web3


def _compile_contract() -> Tuple[list, str]:
    if not SOL_FILE.exists():
        raise FileNotFoundError(f"Contract file not found: {SOL_FILE}")

    source_code = SOL_FILE.read_text(encoding="utf-8")
    install_solc(SOLC_VERSION)

    compiled = compile_standard(
        {
            "language": "Solidity",
            "sources": {"CropInsurance.sol": {"content": source_code}},
            "settings": {
                "outputSelection": {
                    "*": {
                        "*": [
                            "abi",
                            "metadata",
                            "evm.bytecode",
                            "evm.bytecode.sourceMap",
                        ]
                    }
                }
            },
        },
        solc_version=SOLC_VERSION,
    )

    contract = compiled["contracts"]["CropInsurance.sol"]["CropInsurance"]
    abi = contract["abi"]
    bytecode = contract["evm"]["bytecode"]["object"]

    if not bytecode:
        raise RuntimeError("Compiled bytecode is empty.")

    return abi, bytecode


def _deploy(web3: Web3, abi: list, bytecode: str) -> str:
    deployer = web3.eth.accounts[0]
    web3.eth.default_account = deployer

    contract = web3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = contract.constructor().transact({"from": deployer})
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

    if not receipt.contractAddress:
        raise RuntimeError("Deployment failed: no contract address in receipt.")

    return Web3.to_checksum_address(receipt.contractAddress)


def _save_artifacts(abi: list, contract_address: str, web3: Web3) -> None:
    CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)

    ABI_FILE.write_text(json.dumps(abi, indent=2), encoding="utf-8")

    address_payload: Dict[str, Any] = {
        "contract_name": "CropInsurance",
        "address": contract_address,
        "network_url": GANACHE_URL,
        "chain_id": web3.eth.chain_id,
    }
    ADDRESS_FILE.write_text(json.dumps(address_payload, indent=2), encoding="utf-8")


def _update_config_contract_address(contract_address: str) -> None:
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"config.py not found at: {CONFIG_FILE}")

    content = CONFIG_FILE.read_text(encoding="utf-8")

    # Update existing line if present.
    updated = re.sub(
        r"^\s*CONTRACT_ADDRESS\s*=\s*['\"][^'\"]*['\"]",
        f"    CONTRACT_ADDRESS = '{contract_address}'",
        content,
        flags=re.MULTILINE,
    )

    if updated == content:
        # Add CONTRACT_ADDRESS after GANACHE_URL if it doesn't exist.
        anchor = "    GANACHE_URL = 'http://127.0.0.1:7545'"
        if anchor in content:
            updated = content.replace(
                anchor,
                f"{anchor}\n    CONTRACT_ADDRESS = '{contract_address}'",
            )
        else:
            updated = content + f"\n\n# Auto-updated by deploy_contract.py\nCONTRACT_ADDRESS = '{contract_address}'\n"

    CONFIG_FILE.write_text(updated, encoding="utf-8")


def deploy_contract() -> str:
    web3 = _connect_web3()
    abi, bytecode = _compile_contract()
    address = _deploy(web3, abi, bytecode)

    _save_artifacts(abi, address, web3)
    _update_config_contract_address(address)

    return address


def main() -> int:
    print("=" * 60)
    print("CropInsurance Local Contract Deployment")
    print("=" * 60)

    try:
        address = deploy_contract()
        print("\nDeployment completed successfully.")
        print(f"Contract Address: {address}")
        print(f"ABI saved to: {ABI_FILE}")
        print(f"Deployment info saved to: {ADDRESS_FILE}")
        print("config.py updated with new CONTRACT_ADDRESS.")
        return 0
    except Exception as exc:
        print("\nDeployment failed.")
        print(f"Reason: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
