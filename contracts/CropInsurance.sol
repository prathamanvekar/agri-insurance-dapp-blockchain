// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title CropInsurance
 * @dev Smart contract for automated crop insurance with weather & NDVI verification
 */
contract CropInsurance {

    // Contract owner (insurance company)
    address public owner;

    // Policy structure
    struct Policy {
        string policyId;
        address farmer;
        uint256 premium;
        uint256 coverage;
        int256 latitude;      // Stored as lat * 10000
        int256 longitude;     // Stored as lon * 10000
        string cropType;
        bool isActive;
        bool isPremiumPaid;
        bool isClaimed;
        uint256 createdAt;
        uint256 expiresAt;
    }

    // Claim structure
    struct Claim {
        string claimId;
        string policyId;
        bool weatherTrigger;
        bool ndviTrigger;
        string riskType;
        uint256 payoutAmount;
        bool isApproved;
        uint256 processedAt;
    }

    // Mappings
    mapping(string => Policy) public policies;
    mapping(string => Claim) public claims;
    mapping(address => string[]) public farmerPolicies;

    // Arrays for iteration
    string[] public allPolicyIds;
    string[] public allClaimIds;

    // Events
    event PolicyCreated(
        string indexed policyId,
        address indexed farmer,
        uint256 premium,
        uint256 coverage,
        string cropType
    );

    event PremiumPaid(
        string indexed policyId,
        address indexed farmer,
        uint256 amount
    );

    event ClaimSubmitted(
        string indexed claimId,
        string indexed policyId,
        bool weatherTrigger,
        bool ndviTrigger
    );

    event ClaimApproved(
        string indexed claimId,
        string indexed policyId,
        address indexed farmer,
        uint256 payoutAmount
    );

    event ClaimRejected(
        string indexed claimId,
        string indexed policyId,
        string reason
    );

    event PayoutTransferred(
        string indexed policyId,
        address indexed farmer,
        uint256 amount
    );

    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    modifier policyExists(string memory _policyId) {
        require(bytes(policies[_policyId].policyId).length > 0, "Policy does not exist");
        _;
    }

    modifier policyActive(string memory _policyId) {
        require(policies[_policyId].isActive, "Policy is not active");
        _;
    }

    // Constructor
    constructor() {
        owner = msg.sender;
    }

    /**
     * @dev Create a new insurance policy
     */
    function createPolicy(
        string memory _policyId,
        address _farmer,
        uint256 _premium,
        uint256 _coverage,
        int256 _latitude,
        int256 _longitude,
        string memory _cropType
    ) external onlyOwner {
        require(bytes(policies[_policyId].policyId).length == 0, "Policy ID already exists");
        require(_farmer != address(0), "Invalid farmer address");
        require(_premium > 0, "Premium must be greater than 0");
        require(_coverage > 0, "Coverage must be greater than 0");

        Policy memory newPolicy = Policy({
            policyId: _policyId,
            farmer: _farmer,
            premium: _premium,
            coverage: _coverage,
            latitude: _latitude,
            longitude: _longitude,
            cropType: _cropType,
            isActive: false,
            isPremiumPaid: false,
            isClaimed: false,
            createdAt: block.timestamp,
            expiresAt: block.timestamp + 365 days
        });

        policies[_policyId] = newPolicy;
        farmerPolicies[_farmer].push(_policyId);
        allPolicyIds.push(_policyId);

        emit PolicyCreated(_policyId, _farmer, _premium, _coverage, _cropType);
    }

    /**
     * @dev Pay premium for a policy
     */
    function payPremium(string memory _policyId) external payable policyExists(_policyId) {
        Policy storage policy = policies[_policyId];

        require(!policy.isPremiumPaid, "Premium already paid");
        require(msg.value >= policy.premium, "Insufficient premium amount");
        require(msg.sender == policy.farmer, "Only policy farmer can pay premium");

        policy.isPremiumPaid = true;
        policy.isActive = true;

        // Refund excess payment
        if (msg.value > policy.premium) {
            payable(msg.sender).transfer(msg.value - policy.premium);
        }

        emit PremiumPaid(_policyId, msg.sender, policy.premium);
    }

    /**
     * @dev Process claim with double verification (Weather + NDVI triggers)
     */
    function processClaim(
        string memory _claimId,
        string memory _policyId,
        bool _weatherTrigger,
        bool _ndviTrigger,
        string memory _riskType,
        uint256 _payoutAmount
    ) external onlyOwner policyExists(_policyId) policyActive(_policyId) {
        Policy storage policy = policies[_policyId];

        require(!policy.isClaimed, "Policy already claimed");
        require(policy.isPremiumPaid, "Premium not paid");
        require(bytes(claims[_claimId].claimId).length == 0, "Claim ID already exists");

        // Double verification: BOTH triggers must be TRUE
        bool isApproved = _weatherTrigger && _ndviTrigger;

        Claim memory newClaim = Claim({
            claimId: _claimId,
            policyId: _policyId,
            weatherTrigger: _weatherTrigger,
            ndviTrigger: _ndviTrigger,
            riskType: _riskType,
            payoutAmount: isApproved ? _payoutAmount : 0,
            isApproved: isApproved,
            processedAt: block.timestamp
        });

        claims[_claimId] = newClaim;
        allClaimIds.push(_claimId);

        emit ClaimSubmitted(_claimId, _policyId, _weatherTrigger, _ndviTrigger);

        if (isApproved) {
            // Mark policy as claimed
            policy.isClaimed = true;
            policy.isActive = false;

            // Transfer payout to farmer
            require(address(this).balance >= _payoutAmount, "Insufficient contract balance");
            payable(policy.farmer).transfer(_payoutAmount);

            emit ClaimApproved(_claimId, _policyId, policy.farmer, _payoutAmount);
            emit PayoutTransferred(_policyId, policy.farmer, _payoutAmount);
        } else {
            emit ClaimRejected(_claimId, _policyId, "Double verification failed");
        }
    }

    /**
     * @dev Get policy details
     */
    function getPolicy(string memory _policyId) external view returns (
        address farmer,
        uint256 premium,
        uint256 coverage,
        int256 latitude,
        int256 longitude,
        string memory cropType,
        bool isActive,
        bool isPremiumPaid,
        bool isClaimed,
        uint256 createdAt
    ) {
        Policy memory policy = policies[_policyId];
        return (
            policy.farmer,
            policy.premium,
            policy.coverage,
            policy.latitude,
            policy.longitude,
            policy.cropType,
            policy.isActive,
            policy.isPremiumPaid,
            policy.isClaimed,
            policy.createdAt
        );
    }

    /**
     * @dev Get claim details
     */
    function getClaim(string memory _claimId) external view returns (
        string memory policyId,
        bool weatherTrigger,
        bool ndviTrigger,
        string memory riskType,
        uint256 payoutAmount,
        bool isApproved,
        uint256 processedAt
    ) {
        Claim memory claim = claims[_claimId];
        return (
            claim.policyId,
            claim.weatherTrigger,
            claim.ndviTrigger,
            claim.riskType,
            claim.payoutAmount,
            claim.isApproved,
            claim.processedAt
        );
    }

    /**
     * @dev Get all policy IDs for a farmer
     */
    function getFarmerPolicies(address _farmer) external view returns (string[] memory) {
        return farmerPolicies[_farmer];
    }

    /**
     * @dev Get total number of policies
     */
    function getTotalPolicies() external view returns (uint256) {
        return allPolicyIds.length;
    }

    /**
     * @dev Get total number of claims
     */
    function getTotalClaims() external view returns (uint256) {
        return allClaimIds.length;
    }

    /**
     * @dev Get contract balance
     */
    function getContractBalance() external view returns (uint256) {
        return address(this).balance;
    }

    /**
     * @dev Deposit funds to contract (for payouts)
     */
    function depositFunds() external payable onlyOwner {
        require(msg.value > 0, "Must deposit some funds");
    }

    /**
     * @dev Withdraw funds from contract (only owner)
     */
    function withdrawFunds(uint256 _amount) external onlyOwner {
        require(address(this).balance >= _amount, "Insufficient balance");
        payable(owner).transfer(_amount);
    }

    /**
     * @dev Transfer ownership
     */
    function transferOwnership(address _newOwner) external onlyOwner {
        require(_newOwner != address(0), "Invalid address");
        owner = _newOwner;
    }

    // Receive function to accept ETH
    receive() external payable {}
}
