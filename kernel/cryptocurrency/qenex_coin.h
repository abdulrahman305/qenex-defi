#ifndef QENEX_COIN_H
#define QENEX_COIN_H

#include <stdint.h>
#include <time.h>

/* QENEX Coin (QXC) - The Native Currency of QENEX OS */

#define QXC_VERSION 1
#define BLOCK_SIZE 1024
#define DIFFICULTY_ADJUSTMENT_INTERVAL 100
#define INITIAL_REWARD 100.0
#define HALVING_INTERVAL 210000
#define MAX_SUPPLY 21000000.0
#define TRANSACTION_FEE 0.001

/* Mining rewards based on AI improvements */
typedef enum {
    MINING_TYPE_MODEL_ACCURACY = 1,    // Improved AI model accuracy
    MINING_TYPE_TRAINING_SPEED = 2,    // Faster distributed training
    MINING_TYPE_RESOURCE_OPTIMIZE = 3, // Better resource optimization
    MINING_TYPE_ALGORITHM_IMPROVE = 4, // New/improved AI algorithm
    MINING_TYPE_KERNEL_ENHANCE = 5,    // Kernel AI enhancements
    MINING_TYPE_QUANTUM_INTEGRATE = 6, // Quantum computing integration
    MINING_TYPE_SECURITY_PATCH = 7,    // Security improvements
    MINING_TYPE_PERFORMANCE_BOOST = 8  // Performance optimizations
} mining_type_t;

/* Block structure for blockchain */
typedef struct block {
    uint32_t index;
    uint64_t timestamp;
    char prev_hash[65];
    char hash[65];
    uint32_t nonce;
    uint32_t difficulty;
    
    /* AI improvement data */
    struct {
        mining_type_t type;
        double improvement_metric;  // Percentage improvement
        char developer_id[64];
        char model_hash[65];       // Hash of improved AI model
        double reward_amount;
    } ai_mining_data;
    
    /* Transactions in this block */
    struct transaction *transactions;
    uint32_t tx_count;
    
    struct block *next;
    struct block *prev;
} block_t;

/* Transaction structure */
typedef struct transaction {
    char tx_id[65];
    char sender[65];
    char receiver[65];
    double amount;
    double fee;
    uint64_t timestamp;
    char signature[129];
    
    /* AI contribution tracking */
    struct {
        mining_type_t contribution_type;
        double contribution_score;
        char ai_model_ref[65];
    } ai_contribution;
} transaction_t;

/* Wallet structure */
typedef struct wallet {
    char address[65];
    char public_key[129];
    char private_key[257];
    double balance;
    
    /* Developer mining stats */
    struct {
        uint64_t total_contributions;
        double total_mined;
        double accuracy_improvements;
        double speed_improvements;
        uint32_t models_improved;
        uint32_t algorithms_created;
    } mining_stats;
} wallet_t;

/* Mining pool for distributed training */
typedef struct mining_pool {
    char pool_id[65];
    uint32_t active_miners;
    double total_hashrate;
    
    /* Distributed training metrics */
    struct {
        uint32_t active_nodes;
        double total_flops;
        uint64_t models_trained;
        double average_accuracy;
        double training_speed_tps;  // Transactions per second
    } training_metrics;
    
    /* Reward distribution */
    struct {
        double pool_balance;
        double pending_rewards;
        uint32_t payout_interval;
    } rewards;
} mining_pool_t;

/* AI Model improvement verification */
typedef struct ai_verification {
    char model_id[65];
    double baseline_accuracy;
    double improved_accuracy;
    double improvement_percentage;
    
    /* Verification metrics */
    struct {
        uint32_t test_samples;
        double validation_loss;
        double f1_score;
        double precision;
        double recall;
        time_t verification_time;
    } metrics;
    
    /* Consensus from distributed nodes */
    struct {
        uint32_t verifying_nodes;
        uint32_t confirmations;
        double consensus_score;
    } consensus;
} ai_verification_t;

/* Smart contract for automatic mining rewards */
typedef struct mining_contract {
    char contract_id[65];
    char developer_address[65];
    
    /* Conditions for automatic rewards */
    struct {
        double min_accuracy_improvement;  // Minimum 1% improvement
        double min_speed_improvement;      // Minimum 5% faster
        uint32_t min_verifications;        // Minimum 3 node verifications
        double quality_threshold;          // Overall quality score
    } conditions;
    
    /* Automatic execution */
    struct {
        uint8_t auto_execute;
        uint32_t execution_interval;
        double accumulated_reward;
    } execution;
} mining_contract_t;

/* Continuous training reward system */
typedef struct training_reward {
    char node_id[65];
    char model_hash[65];
    
    /* Training contribution metrics */
    struct {
        uint64_t epochs_contributed;
        double compute_hours;
        double bandwidth_gb;
        double storage_gb;
        double gpu_utilization;
    } contribution;
    
    /* Reward calculation */
    struct {
        double base_reward;
        double performance_multiplier;
        double efficiency_bonus;
        double total_reward;
    } reward;
} training_reward_t;

/* Function prototypes */
void qxc_init(void);
wallet_t* create_wallet(const char *developer_id);
block_t* mine_block(wallet_t *miner, ai_verification_t *ai_proof);
int verify_ai_improvement(ai_verification_t *verification);
double calculate_mining_reward(mining_type_t type, double improvement);
int distribute_training_rewards(mining_pool_t *pool);
int process_transaction(transaction_t *tx);
double get_wallet_balance(const char *address);
int verify_blockchain_integrity(void);
void start_continuous_mining(wallet_t *wallet);
int submit_ai_improvement(wallet_t *developer, ai_verification_t *improvement);

/* Distributed training integration */
int integrate_with_distributed_training(void);
double calculate_training_contribution(training_reward_t *reward);
int sync_with_training_nodes(void);

#endif /* QENEX_COIN_H */