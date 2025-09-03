#include "qenex_coin.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <openssl/sha.h>
#include <openssl/rand.h>
#include <pthread.h>
#include <math.h>

/* Global blockchain state */
static block_t *blockchain_head = NULL;
static block_t *blockchain_tail = NULL;
static uint32_t blockchain_height = 0;
static double total_supply = 0.0;
static pthread_mutex_t blockchain_lock = PTHREAD_MUTEX_INITIALIZER;

/* Mining pools for distributed training */
static mining_pool_t *active_pools[100];
static uint32_t pool_count = 0;

/* Continuous training state */
static struct {
    uint8_t active;
    uint32_t training_nodes;
    double total_compute_power;
    uint64_t models_in_training;
    pthread_t training_thread;
} training_state = {0};

/* Initialize QENEX Coin system */
void qxc_init(void) {
    printf("[QXC] Initializing QENEX Coin cryptocurrency system...\n");
    
    /* Create genesis block */
    block_t *genesis = calloc(1, sizeof(block_t));
    genesis->index = 0;
    genesis->timestamp = time(NULL);
    strcpy(genesis->prev_hash, "0");
    genesis->difficulty = 4;
    genesis->ai_mining_data.type = MINING_TYPE_KERNEL_ENHANCE;
    genesis->ai_mining_data.improvement_metric = 100.0;
    strcpy(genesis->ai_mining_data.developer_id, "QENEX_FOUNDATION");
    genesis->ai_mining_data.reward_amount = INITIAL_REWARD;
    
    /* Calculate genesis hash */
    calculate_block_hash(genesis);
    
    blockchain_head = genesis;
    blockchain_tail = genesis;
    blockchain_height = 1;
    total_supply = INITIAL_REWARD;
    
    printf("[QXC] Genesis block created. Initial supply: %.2f QXC\n", total_supply);
    
    /* Start continuous distributed training */
    start_continuous_training();
}

/* Create a new wallet for developer */
wallet_t* create_wallet(const char *developer_id) {
    wallet_t *wallet = calloc(1, sizeof(wallet_t));
    
    /* Generate key pair */
    unsigned char key[32];
    RAND_bytes(key, 32);
    
    /* Generate address from public key */
    SHA256((unsigned char*)developer_id, strlen(developer_id), (unsigned char*)wallet->address);
    for(int i = 0; i < 32; i++) {
        sprintf(&wallet->address[i*2], "%02x", ((unsigned char*)wallet->address)[i]);
    }
    wallet->address[64] = '\0';
    
    /* Initialize mining stats */
    wallet->mining_stats.total_contributions = 0;
    wallet->mining_stats.total_mined = 0.0;
    
    printf("[QXC] Wallet created for developer %s\n", developer_id);
    printf("[QXC] Address: %s\n", wallet->address);
    
    return wallet;
}

/* Mine a new block with AI improvement proof */
block_t* mine_block(wallet_t *miner, ai_verification_t *ai_proof) {
    pthread_mutex_lock(&blockchain_lock);
    
    /* Verify AI improvement */
    if (!verify_ai_improvement(ai_proof)) {
        pthread_mutex_unlock(&blockchain_lock);
        printf("[QXC] AI improvement verification failed\n");
        return NULL;
    }
    
    block_t *new_block = calloc(1, sizeof(block_t));
    new_block->index = blockchain_height;
    new_block->timestamp = time(NULL);
    strcpy(new_block->prev_hash, blockchain_tail->hash);
    new_block->difficulty = calculate_difficulty();
    
    /* Set AI mining data */
    new_block->ai_mining_data.improvement_metric = ai_proof->improvement_percentage;
    strcpy(new_block->ai_mining_data.developer_id, miner->address);
    strcpy(new_block->ai_mining_data.model_hash, ai_proof->model_id);
    
    /* Calculate reward based on improvement */
    double reward = calculate_mining_reward(
        new_block->ai_mining_data.type,
        ai_proof->improvement_percentage
    );
    new_block->ai_mining_data.reward_amount = reward;
    
    /* Proof of AI Work - find nonce */
    uint32_t nonce = 0;
    char target[65];
    memset(target, '0', new_block->difficulty);
    target[new_block->difficulty] = '\0';
    
    while (1) {
        new_block->nonce = nonce;
        calculate_block_hash(new_block);
        
        if (memcmp(new_block->hash, target, new_block->difficulty) <= 0) {
            break;  // Found valid hash
        }
        nonce++;
    }
    
    /* Add block to chain */
    blockchain_tail->next = new_block;
    new_block->prev = blockchain_tail;
    blockchain_tail = new_block;
    blockchain_height++;
    
    /* Update miner's balance and stats */
    miner->balance += reward;
    miner->mining_stats.total_mined += reward;
    miner->mining_stats.total_contributions++;
    
    if (ai_proof->metrics.precision > ai_proof->metrics.validation_loss) {
        miner->mining_stats.accuracy_improvements += ai_proof->improvement_percentage;
        miner->mining_stats.models_improved++;
    }
    
    total_supply += reward;
    
    pthread_mutex_unlock(&blockchain_lock);
    
    printf("[QXC] Block %u mined! Reward: %.4f QXC\n", new_block->index, reward);
    printf("[QXC] AI Improvement: %.2f%% | Total Supply: %.2f QXC\n", 
           ai_proof->improvement_percentage, total_supply);
    
    return new_block;
}

/* Verify AI improvement for mining eligibility */
int verify_ai_improvement(ai_verification_t *verification) {
    /* Check improvement percentage */
    if (verification->improvement_percentage < 1.0) {
        return 0;  // Minimum 1% improvement required
    }
    
    /* Check consensus from distributed nodes */
    if (verification->consensus.confirmations < 3) {
        return 0;  // Need at least 3 confirmations
    }
    
    /* Check consensus score */
    if (verification->consensus.consensus_score < 0.75) {
        return 0;  // Need 75% consensus
    }
    
    /* Verify metrics */
    if (verification->metrics.f1_score < 0.5) {
        return 0;  // Minimum F1 score
    }
    
    return 1;  // Verification passed
}

/* Calculate mining reward based on AI improvement */
double calculate_mining_reward(mining_type_t type, double improvement) {
    double base_reward = INITIAL_REWARD;
    
    /* Halving logic */
    uint32_t halvings = blockchain_height / HALVING_INTERVAL;
    for (uint32_t i = 0; i < halvings; i++) {
        base_reward /= 2.0;
    }
    
    /* Type-based multipliers */
    double type_multiplier = 1.0;
    switch (type) {
        case MINING_TYPE_QUANTUM_INTEGRATE:
            type_multiplier = 3.0;  // Highest reward for quantum integration
            break;
        case MINING_TYPE_ALGORITHM_IMPROVE:
            type_multiplier = 2.5;
            break;
        case MINING_TYPE_MODEL_ACCURACY:
            type_multiplier = 2.0;
            break;
        case MINING_TYPE_KERNEL_ENHANCE:
            type_multiplier = 1.8;
            break;
        case MINING_TYPE_TRAINING_SPEED:
            type_multiplier = 1.5;
            break;
        case MINING_TYPE_SECURITY_PATCH:
            type_multiplier = 1.5;
            break;
        case MINING_TYPE_PERFORMANCE_BOOST:
            type_multiplier = 1.3;
            break;
        case MINING_TYPE_RESOURCE_OPTIMIZE:
            type_multiplier = 1.2;
            break;
    }
    
    /* Improvement-based multiplier (logarithmic scale) */
    double improvement_multiplier = 1.0 + log10(1.0 + improvement / 10.0);
    
    /* Calculate final reward */
    double final_reward = base_reward * type_multiplier * improvement_multiplier;
    
    /* Cap check to prevent inflation */
    if (total_supply + final_reward > MAX_SUPPLY) {
        final_reward = MAX_SUPPLY - total_supply;
    }
    
    return final_reward;
}

/* Continuous distributed training thread */
void* continuous_training_thread(void *arg) {
    printf("[QXC] Starting continuous distributed training...\n");
    
    while (training_state.active) {
        /* Check all active training nodes */
        for (uint32_t i = 0; i < training_state.training_nodes; i++) {
            /* Simulate training progress check */
            double progress = check_training_progress(i);
            
            if (progress >= 100.0) {
                /* Training completed, evaluate improvement */
                ai_verification_t verification;
                evaluate_trained_model(i, &verification);
                
                /* If improvement detected, trigger mining */
                if (verification.improvement_percentage > 0) {
                    trigger_mining_reward(i, &verification);
                }
            }
        }
        
        /* Distribute rewards to training contributors */
        for (uint32_t i = 0; i < pool_count; i++) {
            if (active_pools[i] && active_pools[i]->active_miners > 0) {
                distribute_training_rewards(active_pools[i]);
            }
        }
        
        sleep(10);  // Check every 10 seconds
    }
    
    return NULL;
}

/* Start continuous training and mining */
void start_continuous_training(void) {
    training_state.active = 1;
    training_state.training_nodes = 0;
    training_state.total_compute_power = 0.0;
    training_state.models_in_training = 0;
    
    /* Create training thread */
    pthread_create(&training_state.training_thread, NULL, 
                   continuous_training_thread, NULL);
    
    printf("[QXC] Continuous distributed training activated\n");
}

/* Distribute rewards to training pool participants */
int distribute_training_rewards(mining_pool_t *pool) {
    if (pool->rewards.pending_rewards <= 0) {
        return 0;
    }
    
    double reward_per_miner = pool->rewards.pending_rewards / pool->active_miners;
    
    /* Distribute based on contribution */
    for (uint32_t i = 0; i < pool->active_miners; i++) {
        /* Calculate individual contribution */
        double contribution_factor = calculate_miner_contribution(pool, i);
        double individual_reward = reward_per_miner * contribution_factor;
        
        /* Create reward transaction */
        transaction_t tx;
        generate_transaction_id(&tx);
        strcpy(tx.sender, "MINING_POOL");
        get_miner_address(pool, i, tx.receiver);
        tx.amount = individual_reward;
        tx.fee = TRANSACTION_FEE;
        tx.timestamp = time(NULL);
        tx.ai_contribution.contribution_type = MINING_TYPE_TRAINING_SPEED;
        tx.ai_contribution.contribution_score = contribution_factor;
        
        process_transaction(&tx);
    }
    
    pool->rewards.pending_rewards = 0;
    return 1;
}

/* Calculate block hash */
void calculate_block_hash(block_t *block) {
    char data[4096];
    sprintf(data, "%u%lu%s%u%f%s%f",
            block->index,
            block->timestamp,
            block->prev_hash,
            block->nonce,
            block->ai_mining_data.improvement_metric,
            block->ai_mining_data.developer_id,
            block->ai_mining_data.reward_amount);
    
    unsigned char hash[SHA256_DIGEST_LENGTH];
    SHA256((unsigned char*)data, strlen(data), hash);
    
    for(int i = 0; i < SHA256_DIGEST_LENGTH; i++) {
        sprintf(&block->hash[i*2], "%02x", hash[i]);
    }
    block->hash[64] = '\0';
}

/* Calculate current mining difficulty */
uint32_t calculate_difficulty(void) {
    if (blockchain_height % DIFFICULTY_ADJUSTMENT_INTERVAL != 0) {
        return blockchain_tail->difficulty;
    }
    
    /* Adjust difficulty based on block time */
    block_t *prev_adjustment = blockchain_tail;
    for (int i = 0; i < DIFFICULTY_ADJUSTMENT_INTERVAL - 1 && prev_adjustment->prev; i++) {
        prev_adjustment = prev_adjustment->prev;
    }
    
    uint64_t time_diff = blockchain_tail->timestamp - prev_adjustment->timestamp;
    uint64_t expected_time = DIFFICULTY_ADJUSTMENT_INTERVAL * 60;  // 1 minute per block
    
    uint32_t new_difficulty = blockchain_tail->difficulty;
    if (time_diff < expected_time / 2) {
        new_difficulty++;  // Increase difficulty
    } else if (time_diff > expected_time * 2) {
        if (new_difficulty > 1) new_difficulty--;  // Decrease difficulty
    }
    
    return new_difficulty;
}

/* Submit AI improvement for mining */
int submit_ai_improvement(wallet_t *developer, ai_verification_t *improvement) {
    printf("[QXC] Developer %s submitting AI improvement...\n", developer->address);
    printf("[QXC] Model: %s | Improvement: %.2f%%\n", 
           improvement->model_id, improvement->improvement_percentage);
    
    /* Request verification from distributed nodes */
    request_distributed_verification(improvement);
    
    /* Wait for consensus */
    int attempts = 0;
    while (improvement->consensus.confirmations < 3 && attempts < 30) {
        sleep(1);
        attempts++;
    }
    
    if (improvement->consensus.confirmations >= 3) {
        /* Mine block with improvement */
        block_t *block = mine_block(developer, improvement);
        if (block) {
            printf("[QXC] Mining successful! Developer earned %.4f QXC\n", 
                   block->ai_mining_data.reward_amount);
            return 1;
        }
    }
    
    printf("[QXC] Mining failed - insufficient consensus\n");
    return 0;
}

/* Integrate with distributed training system */
int integrate_with_distributed_training(void) {
    printf("[QXC] Integrating with distributed training system...\n");
    
    /* Create main mining pool */
    mining_pool_t *main_pool = calloc(1, sizeof(mining_pool_t));
    generate_pool_id(main_pool->pool_id);
    main_pool->active_miners = 0;
    main_pool->total_hashrate = 0.0;
    main_pool->training_metrics.active_nodes = 0;
    main_pool->rewards.pool_balance = 0.0;
    main_pool->rewards.payout_interval = 100;  // Every 100 blocks
    
    active_pools[pool_count++] = main_pool;
    
    /* Start training node discovery */
    discover_training_nodes();
    
    printf("[QXC] Distributed training integration complete\n");
    printf("[QXC] Active pools: %u | Training nodes: %u\n", 
           pool_count, training_state.training_nodes);
    
    return 1;
}

/* Process a transaction */
int process_transaction(transaction_t *tx) {
    /* Verify transaction signature */
    if (!verify_transaction_signature(tx)) {
        return 0;
    }
    
    /* Check sender balance */
    double sender_balance = get_wallet_balance(tx->sender);
    if (sender_balance < tx->amount + tx->fee) {
        return 0;
    }
    
    /* Update balances */
    update_balance(tx->sender, -(tx->amount + tx->fee));
    update_balance(tx->receiver, tx->amount);
    
    /* Record AI contribution if present */
    if (tx->ai_contribution.contribution_score > 0) {
        record_ai_contribution(tx->receiver, &tx->ai_contribution);
    }
    
    return 1;
}

/* Get wallet balance */
double get_wallet_balance(const char *address) {
    double balance = 0.0;
    block_t *current = blockchain_head;
    
    while (current) {
        /* Check mining rewards */
        if (strcmp(current->ai_mining_data.developer_id, address) == 0) {
            balance += current->ai_mining_data.reward_amount;
        }
        
        /* Check transactions */
        for (uint32_t i = 0; i < current->tx_count; i++) {
            if (strcmp(current->transactions[i].receiver, address) == 0) {
                balance += current->transactions[i].amount;
            }
            if (strcmp(current->transactions[i].sender, address) == 0) {
                balance -= (current->transactions[i].amount + current->transactions[i].fee);
            }
        }
        
        current = current->next;
    }
    
    return balance;
}

/* Verify blockchain integrity */
int verify_blockchain_integrity(void) {
    printf("[QXC] Verifying blockchain integrity...\n");
    
    block_t *current = blockchain_head;
    uint32_t verified_blocks = 0;
    
    while (current && current->next) {
        /* Verify hash linkage */
        if (strcmp(current->hash, current->next->prev_hash) != 0) {
            printf("[QXC] ERROR: Hash mismatch at block %u\n", current->index);
            return 0;
        }
        
        /* Recalculate and verify hash */
        char original_hash[65];
        strcpy(original_hash, current->hash);
        calculate_block_hash(current);
        
        if (strcmp(original_hash, current->hash) != 0) {
            printf("[QXC] ERROR: Invalid hash at block %u\n", current->index);
            return 0;
        }
        
        verified_blocks++;
        current = current->next;
    }
    
    printf("[QXC] Blockchain verified: %u blocks valid\n", verified_blocks);
    return 1;
}

/* Start continuous mining for a wallet */
void start_continuous_mining(wallet_t *wallet) {
    printf("[QXC] Starting continuous mining for wallet %s\n", wallet->address);
    
    /* Join main mining pool */
    if (pool_count > 0 && active_pools[0]) {
        active_pools[0]->active_miners++;
        register_miner_in_pool(active_pools[0], wallet);
    }
    
    /* Start local training node */
    start_local_training_node(wallet);
    training_state.training_nodes++;
    
    printf("[QXC] Miner registered. Active miners: %u\n", 
           active_pools[0]->active_miners);
}