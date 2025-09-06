/*
 * POSIX/UNIX Compatibility Layer for QENEX Kernel
 */

#include "../universal_kernel.h"
#include <sys/types.h>
#include <unistd.h>
#include <fcntl.h>

/* POSIX System Call Translation Table */
static const struct {
    int posix_syscall;
    int qenex_syscall;
    const char* name;
} posix_syscall_map[] = {
    {0, SYSCALL_READ, "read"},
    {1, SYSCALL_WRITE, "write"},
    {2, SYSCALL_OPEN, "open"},
    {3, SYSCALL_CLOSE, "close"},
    {4, SYSCALL_STAT, "stat"},
    {5, SYSCALL_FSTAT, "fstat"},
    {57, SYSCALL_FORK, "fork"},
    {59, SYSCALL_EXECVE, "execve"},
    {60, SYSCALL_EXIT, "exit"},
    {61, SYSCALL_WAIT4, "wait4"},
    {62, SYSCALL_KILL, "kill"},
    {9, SYSCALL_MMAP, "mmap"},
    {11, SYSCALL_MUNMAP, "munmap"},
};

/* POSIX Signal Handling */
typedef struct {
    int signal_num;
    void (*handler)(int);
    sigset_t mask;
} posix_signal_t;

/* Convert POSIX file descriptor to universal file handle */
universal_file_t* fd_to_universal(int fd) {
    universal_file_t* uf = allocate_universal_file();
    uf->unix_fd = fd;
    uf->qenex_handle = generate_qenex_handle();
    
    // Map POSIX permissions to universal
    struct stat st;
    if (fstat(fd, &st) == 0) {
        uf->permissions = posix_to_universal_perms(st.st_mode);
        uf->size = st.st_size;
    }
    
    return uf;
}

/* POSIX fork() implementation */
pid_t posix_fork(void) {
    universal_syscall_t syscall = {
        .syscall_id = SYSCALL_FORK,
        .args = {0},
        .compatibility = "posix"
    };
    
    int64_t result = universal_syscall(&syscall);
    
    if (result == 0) {
        // Child process
        return 0;
    } else if (result > 0) {
        // Parent process
        return (pid_t)result;
    } else {
        // Error
        errno = -result;
        return -1;
    }
}

/* POSIX exec() family implementation */
int posix_execve(const char* path, char* const argv[], char* const envp[]) {
    universal_syscall_t syscall = {
        .syscall_id = SYSCALL_EXEC,
        .args = {(uint64_t)path, (uint64_t)argv, (uint64_t)envp},
        .compatibility = "posix"
    };
    
    return universal_syscall(&syscall);
}

/* POSIX file operations */
int posix_open(const char* pathname, int flags, mode_t mode) {
    universal_syscall_t syscall = {
        .syscall_id = SYSCALL_OPEN,
        .args = {(uint64_t)pathname, flags, mode},
        .compatibility = "posix"
    };
    
    int64_t handle = universal_syscall(&syscall);
    
    // Convert QENEX handle to POSIX fd
    return universal_to_fd(handle);
}

/* POSIX memory mapping */
void* posix_mmap(void* addr, size_t length, int prot, int flags, 
                 int fd, off_t offset) {
    universal_syscall_t syscall = {
        .syscall_id = SYSCALL_MMAP,
        .args = {(uint64_t)addr, length, prot, flags, fd, offset},
        .compatibility = "posix",
        .use_quantum = (length > 1024*1024)  // Use quantum for large allocations
    };
    
    return (void*)universal_syscall(&syscall);
}

/* POSIX thread support (pthreads) */
typedef struct {
    universal_pid_t* upid;
    void* (*start_routine)(void*);
    void* arg;
    void* stack;
    size_t stack_size;
} pthread_internal_t;

int pthread_create_qenex(pthread_t* thread, const pthread_attr_t* attr,
                         void* (*start_routine)(void*), void* arg) {
    pthread_internal_t* pt = allocate_pthread();
    pt->start_routine = start_routine;
    pt->arg = arg;
    
    // Create quantum-entangled thread for better performance
    universal_syscall_t syscall = {
        .syscall_id = SYSCALL_CREATE_THREAD,
        .args = {(uint64_t)pt, 0, 0},
        .use_quantum = true
    };
    
    pt->upid = (universal_pid_t*)universal_syscall(&syscall);
    *thread = (pthread_t)pt;
    
    return 0;
}

/* POSIX shared memory */
int posix_shm_open(const char* name, int oflag, mode_t mode) {
    universal_syscall_t syscall = {
        .syscall_id = SYSCALL_SHM_OPEN,
        .args = {(uint64_t)name, oflag, mode},
        .compatibility = "posix"
    };
    
    return universal_syscall(&syscall);
}

/* Initialize POSIX compatibility layer */
void init_posix_compatibility(void) {
    // Register POSIX syscall handlers
    for (int i = 0; i < sizeof(posix_syscall_map)/sizeof(posix_syscall_map[0]); i++) {
        register_syscall_translator(
            posix_syscall_map[i].posix_syscall,
            posix_syscall_map[i].qenex_syscall,
            "posix"
        );
    }
    
    // Initialize POSIX signal handling
    init_posix_signals();
    
    // Set up POSIX filesystem semantics
    init_posix_filesystem();
    
    printk("POSIX compatibility layer initialized\n");
}