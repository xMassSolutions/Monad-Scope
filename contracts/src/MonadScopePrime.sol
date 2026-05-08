// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IERC20 {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/// @title MonadScopePrime
/// @notice Pay-to-analyze (in USDC) + on-chain verdict attestation for Monad Scope.
///         Users approve `price` USDC and call requestAnalysis to commission a
///         Prime deep-analysis. The backend attestor publishes verdicts on-chain
///         so the public case library is tamper-evident.
contract MonadScopePrime {
    // --- roles ---
    address public owner;
    address public attestor;

    // --- payment token ---
    IERC20 public immutable paymentToken;

    // --- pricing (in token's smallest unit; USDC = 6 decimals) ---
    uint256 public price;

    // --- jobs ---
    uint256 public nextJobId;

    struct Job {
        address payer;
        address target;
        uint256 amount;
        uint64 paidAt;
        bool fulfilled;
    }

    mapping(uint256 => Job) public jobs;

    // --- verdicts (latest per target) ---
    struct Verdict {
        uint8 riskScore;
        uint8 confidence;
        bytes32 classification;
        uint32 rulesetVersion;
        bytes32 findingsHash;
        uint64 attestedAt;
        uint256 jobId;
    }

    mapping(address => Verdict) public verdicts;

    // --- events ---
    event PrimePaid(
        uint256 indexed jobId,
        address indexed target,
        address indexed payer,
        uint256 amount
    );
    event VerdictAttested(
        address indexed target,
        uint256 indexed jobId,
        uint8 riskScore,
        uint8 confidence,
        bytes32 classification,
        uint32 rulesetVersion,
        bytes32 findingsHash
    );
    event PriceUpdated(uint256 oldPrice, uint256 newPrice);
    event AttestorUpdated(address oldAttestor, address newAttestor);
    event OwnerUpdated(address oldOwner, address newOwner);
    event Withdrawn(address indexed to, uint256 amount);

    // --- errors ---
    error NotOwner();
    error NotAttestor();
    error ZeroAddress();
    error TransferFailed();
    error UnknownJob();
    error AlreadyFulfilled();
    error JobTargetMismatch();
    error InvalidScore();
    error NoNativePayments();

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    modifier onlyAttestor() {
        if (msg.sender != attestor) revert NotAttestor();
        _;
    }

    constructor(address _paymentToken, address _attestor, uint256 _price) {
        if (_paymentToken == address(0) || _attestor == address(0)) revert ZeroAddress();
        owner = msg.sender;
        attestor = _attestor;
        paymentToken = IERC20(_paymentToken);
        price = _price;
        nextJobId = 1;
        emit OwnerUpdated(address(0), msg.sender);
        emit AttestorUpdated(address(0), _attestor);
        emit PriceUpdated(0, _price);
    }

    // --- user path ---

    /// @notice Pay `price` USDC to commission Prime analysis of `target`.
    ///         Caller must `approve(this, price)` on the USDC contract first.
    function requestAnalysis(address target) external returns (uint256 jobId) {
        if (target == address(0)) revert ZeroAddress();
        uint256 amount = price;

        bool ok = paymentToken.transferFrom(msg.sender, address(this), amount);
        if (!ok) revert TransferFailed();

        jobId = nextJobId++;
        jobs[jobId] = Job({
            payer: msg.sender,
            target: target,
            amount: amount,
            paidAt: uint64(block.timestamp),
            fulfilled: false
        });

        emit PrimePaid(jobId, target, msg.sender, amount);
    }

    // --- attestor path ---

    function attestVerdict(
        address target,
        uint256 jobId,
        uint8 riskScore,
        uint8 confidence,
        bytes32 classification,
        uint32 rulesetVersion,
        bytes32 findingsHash
    ) external onlyAttestor {
        if (target == address(0)) revert ZeroAddress();
        if (riskScore > 100 || confidence > 100) revert InvalidScore();

        if (jobId != 0) {
            Job storage j = jobs[jobId];
            if (j.payer == address(0)) revert UnknownJob();
            if (j.fulfilled) revert AlreadyFulfilled();
            if (j.target != target) revert JobTargetMismatch();
            j.fulfilled = true;
        }

        verdicts[target] = Verdict({
            riskScore: riskScore,
            confidence: confidence,
            classification: classification,
            rulesetVersion: rulesetVersion,
            findingsHash: findingsHash,
            attestedAt: uint64(block.timestamp),
            jobId: jobId
        });

        emit VerdictAttested(
            target,
            jobId,
            riskScore,
            confidence,
            classification,
            rulesetVersion,
            findingsHash
        );
    }

    // --- views ---

    function getVerdict(address target) external view returns (Verdict memory) {
        return verdicts[target];
    }

    function hasVerdict(address target) external view returns (bool) {
        return verdicts[target].attestedAt != 0;
    }

    // --- admin ---

    function setPrice(uint256 newPrice) external onlyOwner {
        emit PriceUpdated(price, newPrice);
        price = newPrice;
    }

    function setAttestor(address newAttestor) external onlyOwner {
        if (newAttestor == address(0)) revert ZeroAddress();
        emit AttestorUpdated(attestor, newAttestor);
        attestor = newAttestor;
    }

    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert ZeroAddress();
        emit OwnerUpdated(owner, newOwner);
        owner = newOwner;
    }

    function withdraw(address to, uint256 amount) external onlyOwner {
        if (to == address(0)) revert ZeroAddress();
        bool ok = paymentToken.transfer(to, amount);
        if (!ok) revert TransferFailed();
        emit Withdrawn(to, amount);
    }

    // reject native MON sends; this contract is USDC-only
    receive() external payable {
        revert NoNativePayments();
    }
}
