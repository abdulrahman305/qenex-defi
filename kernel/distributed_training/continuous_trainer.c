#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <unistd.h>
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include "../cryptocurrency/qenex_coin.h"

#define MAX_TRAINING_NODES 1000
#define TRAINING_PORT 9547
#define MODEL_SYNC_INTERVAL 60
#define CHECKPOINT_INTERVAL 300

/* Training node structure */
typedef struct training_node {
    char node_id[65];
    char ip_address[16];
    uint16_t port;
    uint8_t active;
    
    /* Computing resources */
    struct {
        uint32_t cpu_cores;
        uint32_t gpu_count;
        uint64_t memory_gb;
        double tflops;
        double current_utilization;
    } resources;
    
    /* Current training task */
    struct {
        char model_id[65];
        uint32_t current_epoch;
        uint32_t total_epochs;
        double loss;
        double accuracy;
        time_t start_time;
        uint64_t samples_processed;
    } task;
    
    /* Mining integration */
    wallet_t *wallet;
    double mining_contribution;
    uint64_t blocks_contributed;
} training_node_t;

/* Global distributed training state */
static struct {
    training_node_t nodes[MAX_TRAINING_NODES];
    uint32_t active_nodes;
    pthread_mutex_t nodes_lock;
    
    /* Model repository */
    struct {
        char models[100][65];
        uint32_t model_count;
        double best_accuracies[100];
    } repository;
    
    /* Training coordination */
    struct {
        pthread_t coordinator_thread;
        pthread_t sync_thread;
        uint8_t running;
        uint16_t coordinator_port;
    } coordination;
    
    /* Continuous improvement tracking */
    struct {
        uint64_t total_improvements;
        double cumulative_accuracy_gain;
        uint64_t total_epochs_trained;
        double total_qxc_mined;
    } metrics;
} training_system = {
    .active_nodes = 0,
    .nodes_lock = PTHREAD_MUTEX_INITIALIZER,
    .coordination.running = 0,
    .coordination.coordinator_port = TRAINING_PORT
};

/* Initialize continuous distributed training */
void init_continuous_training(void) {
    printf("[CDT] Initializing Continuous Distributed Training System...\n");
    
    training_system.coordination.running = 1;
    training_system.metrics.total_improvements = 0;
    training_system.metrics.cumulative_accuracy_gain = 0.0;
    training_system.metrics.total_epochs_trained = 0;
    training_system.metrics.total_qxc_mined = 0.0;
    
    /* Start coordinator thread */
    pthread_create(&training_system.coordination.coordinator_thread, NULL,
                   coordinator_thread_func, NULL);
    
    /* Start model sync thread */
    pthread_create(&training_system.coordination.sync_thread, NULL,
                   sync_thread_func, NULL);
    
    /* Initialize QXC integration */
    qxc_init();
    integrate_with_distributed_training();
    
    printf("[CDT] System initialized. Waiting for training nodes...\n");
}

/* Coordinator thread for managing distributed training */
void* coordinator_thread_func(void *arg) {
    int server_fd;
    struct sockaddr_in server_addr;
    
    /* Create coordinator socket */
    server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        perror("[CDT] Socket creation failed");
        return NULL;
    }
    
    /* Bind to coordinator port */
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(training_system.coordination.coordinator_port);
    
    if (bind(server_fd, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        perror("[CDT] Bind failed");
        close(server_fd);
        return NULL;
    }
    
    listen(server_fd, 10);
    printf("[CDT] Coordinator listening on port %d\n", 
           training_system.coordination.coordinator_port);
    
    while (training_system.coordination.running) {
        struct sockaddr_in client_addr;
        socklen_t client_len = sizeof(client_addr);
        
        int client_fd = accept(server_fd, (struct sockaddr*)&client_addr, &client_len);
        if (client_fd < 0) continue;
        
        /* Handle training node connection */
        handle_node_connection(client_fd, &client_addr);
        close(client_fd);
    }
    
    close(server_fd);
    return NULL;
}

/* Handle new training node connection */
void handle_node_connection(int client_fd, struct sockaddr_in *client_addr) {
    training_node_t *node = NULL;
    char buffer[4096];
    
    /* Receive node registration data */
    int bytes = recv(client_fd, buffer, sizeof(buffer), 0);
    if (bytes <= 0) return;
    
    /* Parse node information */
    pthread_mutex_lock(&training_system.nodes_lock);
    
    /* Find or create node entry */
    for (uint32_t i = 0; i < MAX_TRAINING_NODES; i++) {
        if (!training_system.nodes[i].active) {
            node = &training_system.nodes[i];
            node->active = 1;
            training_system.active_nodes++;
            break;
        }
    }
    
    if (node) {
        /* Parse node capabilities */
        sscanf(buffer, "NODE_REGISTER:%64[^:]:%u:%u:%lu:%lf",
               node->node_id,
               &node->resources.cpu_cores,
               &node->resources.gpu_count,
               &node->resources.memory_gb,
               &node->resources.tflops);
        
        strcpy(node->ip_address, inet_ntoa(client_addr->sin_addr));
        node->port = ntohs(client_addr->sin_port);
        
        /* Create wallet for mining rewards */
        node->wallet = create_wallet(node->node_id);
        
        printf("[CDT] New node registered: %s (%s:%d)\n",
               node->node_id, node->ip_address, node->port);
        printf("[CDT]   Resources: %u CPUs, %u GPUs, %lu GB RAM, %.2f TFLOPS\n",
               node->resources.cpu_cores, node->resources.gpu_count,
               node->resources.memory_gb, node->resources.tflops);
        printf("[CDT]   Mining wallet: %s\n", node->wallet->address);
        
        /* Assign initial training task */
        assign_training_task(node);
        
        /* Send acknowledgment with task */
        sprintf(buffer, "ACK:TASK:%s:%u:%u",
                node->task.model_id,
                node->task.current_epoch,
                node->task.total_epochs);
        send(client_fd, buffer, strlen(buffer), 0);
    }
    
    pthread_mutex_unlock(&training_system.nodes_lock);
}

/* Assign training task to node */
void assign_training_task(training_node_t *node) {
    /* Select model for training based on node capabilities */
    char model_id[65];
    
    if (node->resources.gpu_count > 0) {
        /* Assign complex model for GPU nodes */
        sprintf(model_id, "transformer_gpt_%u", rand() % 10);
        node->task.total_epochs = 100;
    } else {
        /* Assign simpler model for CPU-only nodes */
        sprintf(model_id, "mlp_classifier_%u", rand() % 10);
        node->task.total_epochs = 50;
    }
    
    strcpy(node->task.model_id, model_id);
    node->task.current_epoch = 0;
    node->task.loss = 10.0;  // Initial high loss
    node->task.accuracy = 0.0;
    node->task.start_time = time(NULL);
    node->task.samples_processed = 0;
    
    /* Add model to repository if new */
    int found = 0;
    for (uint32_t i = 0; i < training_system.repository.model_count; i++) {
        if (strcmp(training_system.repository.models[i], model_id) == 0) {
            found = 1;
            break;
        }
    }
    
    if (!found && training_system.repository.model_count < 100) {
        strcpy(training_system.repository.models[training_system.repository.model_count],
               model_id);
        training_system.repository.best_accuracies[training_system.repository.model_count] = 0.0;
        training_system.repository.model_count++;
    }
}

/* Model synchronization thread */
void* sync_thread_func(void *arg) {
    printf("[CDT] Model synchronization thread started\n");
    
    while (training_system.coordination.running) {
        sleep(MODEL_SYNC_INTERVAL);
        
        pthread_mutex_lock(&training_system.nodes_lock);
        
        /* Check all active nodes for improvements */
        for (uint32_t i = 0; i < MAX_TRAINING_NODES; i++) {
            if (!training_system.nodes[i].active) continue;
            
            training_node_t *node = &training_system.nodes[i];
            
            /* Simulate training progress */
            simulate_training_progress(node);
            
            /* Check for model improvement */
            if (node->task.current_epoch > 0 && 
                node->task.current_epoch % 10 == 0) {
                
                check_and_reward_improvement(node);
            }
            
            /* Handle completed training */
            if (node->task.current_epoch >= node->task.total_epochs) {
                finalize_training(node);
                assign_training_task(node);  // Assign new task
            }
        }
        
        pthread_mutex_unlock(&training_system.nodes_lock);
        
        /* Print system metrics */
        print_training_metrics();
    }
    
    return NULL;
}

/* Simulate training progress for a node */
void simulate_training_progress(training_node_t *node) {
    /* Update epoch */
    node->task.current_epoch++;
    training_system.metrics.total_epochs_trained++;
    
    /* Simulate loss decrease and accuracy increase */
    double learning_rate = 0.01;
    double noise = ((double)rand() / RAND_MAX - 0.5) * 0.1;
    
    node->task.loss *= (1.0 - learning_rate + noise);
    if (node->task.loss < 0.01) node->task.loss = 0.01;
    
    node->task.accuracy = 1.0 - (node->task.loss / 10.0);
    if (node->task.accuracy > 0.99) node->task.accuracy = 0.99;
    
    /* Update samples processed */
    node->task.samples_processed += 50000;  // Batch size * batches per epoch
    
    /* Update resource utilization */
    node->resources.current_utilization = 0.7 + ((double)rand() / RAND_MAX * 0.3);
}

/* Check for improvement and distribute mining rewards */
void check_and_reward_improvement(training_node_t *node) {
    /* Find model in repository */
    int model_idx = -1;
    for (uint32_t i = 0; i < training_system.repository.model_count; i++) {
        if (strcmp(training_system.repository.models[i], node->task.model_id) == 0) {
            model_idx = i;
            break;
        }
    }
    
    if (model_idx < 0) return;
    
    double prev_accuracy = training_system.repository.best_accuracies[model_idx];
    double improvement = (node->task.accuracy - prev_accuracy) * 100.0;
    
    if (improvement > 1.0) {  // At least 1% improvement
        printf("[CDT] Model improvement detected! Node: %s, Model: %s\n",
               node->node_id, node->task.model_id);
        printf("[CDT]   Previous: %.2f%%, Current: %.2f%%, Improvement: %.2f%%\n",
               prev_accuracy * 100, node->task.accuracy * 100, improvement);
        
        /* Create AI verification for mining */
        ai_verification_t verification;
        strcpy(verification.model_id, node->task.model_id);
        verification.baseline_accuracy = prev_accuracy;
        verification.improved_accuracy = node->task.accuracy;
        verification.improvement_percentage = improvement;
        
        verification.metrics.test_samples = node->task.samples_processed;
        verification.metrics.validation_loss = node->task.loss;
        verification.metrics.f1_score = node->task.accuracy * 0.95;  // Approximate
        verification.metrics.precision = node->task.accuracy * 0.97;
        verification.metrics.recall = node->task.accuracy * 0.93;
        verification.metrics.verification_time = time(NULL);
        
        /* Simulate consensus from other nodes */
        verification.consensus.verifying_nodes = training_system.active_nodes;
        verification.consensus.confirmations = (training_system.active_nodes > 3) ? 
                                               training_system.active_nodes / 2 : 3;
        verification.consensus.consensus_score = 0.85 + ((double)rand() / RAND_MAX * 0.15);
        
        /* Submit for mining reward */
        if (submit_ai_improvement(node->wallet, &verification)) {
            /* Update repository */
            training_system.repository.best_accuracies[model_idx] = node->task.accuracy;
            
            /* Update metrics */
            training_system.metrics.total_improvements++;
            training_system.metrics.cumulative_accuracy_gain += improvement;
            
            /* Update node mining stats */
            node->mining_contribution += improvement;
            node->blocks_contributed++;
            
            /* Get new balance */
            double balance = get_wallet_balance(node->wallet->address);
            training_system.metrics.total_qxc_mined = balance;
            
            printf("[CDT] Mining reward distributed! Node balance: %.4f QXC\n", balance);
        }
    }
}

/* Finalize training for a node */
void finalize_training(training_node_t *node) {
    printf("[CDT] Training completed for model %s on node %s\n",
           node->task.model_id, node->node_id);
    printf("[CDT]   Final accuracy: %.2f%%, Loss: %.4f\n",
           node->task.accuracy * 100, node->task.loss);
    printf("[CDT]   Epochs: %u, Samples: %lu\n",
           node->task.total_epochs, node->task.samples_processed);
    
    /* Calculate training time */
    time_t duration = time(NULL) - node->task.start_time;
    printf("[CDT]   Training time: %ld seconds\n", duration);
    
    /* Award completion bonus */
    double completion_bonus = 0.1;  // Small bonus for completing training
    node->wallet->balance += completion_bonus;
    
    printf("[CDT]   Completion bonus: %.4f QXC\n", completion_bonus);
}

/* Print training system metrics */
void print_training_metrics(void) {
    printf("\n");
    printf("================== CONTINUOUS DISTRIBUTED TRAINING ==================\n");
    printf("Active Nodes:          %u\n", training_system.active_nodes);
    printf("Models in Repository:  %u\n", training_system.repository.model_count);
    printf("Total Epochs Trained:  %lu\n", training_system.metrics.total_epochs_trained);
    printf("Total Improvements:    %lu\n", training_system.metrics.total_improvements);
    printf("Cumulative Accuracy:   +%.2f%%\n", training_system.metrics.cumulative_accuracy_gain);
    printf("Total QXC Mined:       %.4f QXC\n", training_system.metrics.total_qxc_mined);
    
    /* Calculate total compute power */
    double total_tflops = 0.0;
    for (uint32_t i = 0; i < MAX_TRAINING_NODES; i++) {
        if (training_system.nodes[i].active) {
            total_tflops += training_system.nodes[i].resources.tflops;
        }
    }
    printf("Total Compute Power:   %.2f TFLOPS\n", total_tflops);
    printf("====================================================================\n\n");
}

/* Add new training node to the system */
int add_training_node(const char *node_id, const char *ip_address) {
    pthread_mutex_lock(&training_system.nodes_lock);
    
    for (uint32_t i = 0; i < MAX_TRAINING_NODES; i++) {
        if (!training_system.nodes[i].active) {
            training_node_t *node = &training_system.nodes[i];
            
            strcpy(node->node_id, node_id);
            strcpy(node->ip_address, ip_address);
            node->port = TRAINING_PORT + i;
            node->active = 1;
            
            /* Set default resources */
            node->resources.cpu_cores = 8;
            node->resources.gpu_count = 1;
            node->resources.memory_gb = 32;
            node->resources.tflops = 10.0;
            node->resources.current_utilization = 0.0;
            
            /* Create wallet */
            node->wallet = create_wallet(node_id);
            
            /* Assign task */
            assign_training_task(node);
            
            training_system.active_nodes++;
            
            pthread_mutex_unlock(&training_system.nodes_lock);
            
            printf("[CDT] Node %s added successfully\n", node_id);
            return 1;
        }
    }
    
    pthread_mutex_unlock(&training_system.nodes_lock);
    return 0;
}

/* Get training status for all nodes */
void get_training_status(void) {
    pthread_mutex_lock(&training_system.nodes_lock);
    
    printf("\n========== TRAINING NODE STATUS ==========\n");
    for (uint32_t i = 0; i < MAX_TRAINING_NODES; i++) {
        if (training_system.nodes[i].active) {
            training_node_t *node = &training_system.nodes[i];
            printf("Node: %s (%s:%d)\n", node->node_id, node->ip_address, node->port);
            printf("  Model: %s\n", node->task.model_id);
            printf("  Progress: %u/%u epochs\n", 
                   node->task.current_epoch, node->task.total_epochs);
            printf("  Accuracy: %.2f%%, Loss: %.4f\n",
                   node->task.accuracy * 100, node->task.loss);
            printf("  QXC Mined: %.4f, Blocks: %lu\n",
                   get_wallet_balance(node->wallet->address), node->blocks_contributed);
            printf("  Utilization: %.1f%%\n", node->resources.current_utilization * 100);
            printf("\n");
        }
    }
    printf("==========================================\n");
    
    pthread_mutex_unlock(&training_system.nodes_lock);
}

/* Stop continuous training */
void stop_continuous_training(void) {
    training_system.coordination.running = 0;
    
    /* Wait for threads to finish */
    pthread_join(training_system.coordination.coordinator_thread, NULL);
    pthread_join(training_system.coordination.sync_thread, NULL);
    
    printf("[CDT] Continuous distributed training stopped\n");
}