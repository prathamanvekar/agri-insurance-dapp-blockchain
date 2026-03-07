// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract CropInsurance {
    address public owner;

    struct Policy {
        string policyId;
        address farmer;
        uint256 premium;
        uint256 coverage;
        string cropType;
        bool premiumPaid;
        bool active;
        bool claimed;
        uint256 createdAt;
    }

    struct Claim {
        string claimId;
        string policyId;
        bool weatherTrigger;
        bool ndviTrigger;
        bool approved;
        uint256 payoutAmount;
        uint256 processedAt;
    }

    mapping(string => Policy) private policies;
    mapping(string => Claim) private claims;

    event PolicyCreated(
        string indexed policyId,
        address indexed farmer,
        uint256 premium,
        uint256 coverage,
        string cropType
    );

    event PremiumPaid(
        string indexed policyId,
        address indexed payer,
        uint256 amount
    );

    event ClaimProcessed(
        string indexed claimId,
        string indexed policyId,
        bool weatherTrigger,
        bool ndviTrigger,
        bool approved,
        uint256 payoutAmount
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    modifier policyExists(string memory policyId) {
        require(bytes(policies[policyId].policyId).length > 0, "Policy not found");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function createPolicy(
        string memory policyId,
        address farmer,
        uint256 premium,
        uint256 coverage,
        string memory cropType
    ) external onlyOwner {
        require(bytes(policyId).length > 0, "policyId required");
        require(farmer != address(0), "invalid farmer");
        require(premium > 0, "premium must be > 0");
        require(coverage > 0, "coverage must be > 0");
        require(bytes(policies[policyId].policyId).length == 0, "policy already exists");

        policies[policyId] = Policy({
            policyId: policyId,
            farmer: farmer,
            premium: premium,
            coverage: coverage,
            cropType: cropType,
            premiumPaid: false,
            active: false,
            claimed: false,
            createdAt: block.timestamp
        });

        emit PolicyCreated(policyId, farmer, premium, coverage, cropType);
    }

    function payPremium(string memory policyId) external payable policyExists(policyId) {
        Policy storage policy = policies[policyId];
        require(!policy.premiumPaid, "premium already paid");
        require(msg.value >= policy.premium, "insufficient premium");
        require(msg.sender == policy.farmer || msg.sender == owner, "unauthorized payer");

        policy.premiumPaid = true;
        policy.active = true;

        if (msg.value > policy.premium) {
            payable(msg.sender).transfer(msg.value - policy.premium);
        }

        emit PremiumPaid(policyId, msg.sender, policy.premium);
    }

    function processClaim(
        string memory claimId,
        string memory policyId,
        bool weatherTrigger,
        bool ndviTrigger,
        uint256 payoutAmount
    ) external onlyOwner policyExists(policyId) {
        require(bytes(claimId).length > 0, "claimId required");
        require(bytes(claims[claimId].claimId).length == 0, "claim already exists");

        Policy storage policy = policies[policyId];
        require(policy.premiumPaid, "premium not paid");
        require(policy.active, "policy inactive");
        require(!policy.claimed, "policy already claimed");

        bool approved = weatherTrigger && ndviTrigger;
        uint256 finalPayout = approved ? payoutAmount : 0;

        claims[claimId] = Claim({
            claimId: claimId,
            policyId: policyId,
            weatherTrigger: weatherTrigger,
            ndviTrigger: ndviTrigger,
            approved: approved,
            payoutAmount: finalPayout,
            processedAt: block.timestamp
        });

        if (approved) {
            require(address(this).balance >= finalPayout, "insufficient contract balance");
            policy.claimed = true;
            policy.active = false;
            payable(policy.farmer).transfer(finalPayout);
        }

        emit ClaimProcessed(
            claimId,
            policyId,
            weatherTrigger,
            ndviTrigger,
            approved,
            finalPayout
        );
    }

    function getPolicy(string memory policyId)
        external
        view
        returns (
            string memory _policyId,
            address farmer,
            uint256 premium,
            uint256 coverage,
            string memory cropType,
            bool premiumPaid,
            bool active,
            bool claimed,
            uint256 createdAt
        )
    {
        Policy memory p = policies[policyId];
        require(bytes(p.policyId).length > 0, "Policy not found");

        return (
            p.policyId,
            p.farmer,
            p.premium,
            p.coverage,
            p.cropType,
            p.premiumPaid,
            p.active,
            p.claimed,
            p.createdAt
        );
    }

    function getClaim(string memory claimId)
        external
        view
        returns (
            string memory _claimId,
            string memory policyId,
            bool weatherTrigger,
            bool ndviTrigger,
            bool approved,
            uint256 payoutAmount,
            uint256 processedAt
        )
    {
        Claim memory c = claims[claimId];
        require(bytes(c.claimId).length > 0, "Claim not found");

        return (
            c.claimId,
            c.policyId,
            c.weatherTrigger,
            c.ndviTrigger,
            c.approved,
            c.payoutAmount,
            c.processedAt
        );
    }

    receive() external payable {}
}
