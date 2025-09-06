# QENEX Universal Kernel Makefile

KERNEL_VERSION = 1.0.0
CC = gcc
AS = as
LD = ld
CFLAGS = -Wall -O2 -fno-builtin -nostdinc -nostdlib -m64
LDFLAGS = -T kernel.ld -nostdlib

# Kernel source files
KERNEL_SRCS = \
	universal_kernel.c \
	qenex_integration.c \
	compatibility/posix_layer.c \
	compatibility/windows_layer.c \
	quantum/quantum_scheduler.c \
	ai/kernel_ai.c \
	memory/ai_memory.c \
	drivers/universal_driver.c

KERNEL_OBJS = $(KERNEL_SRCS:.c=.o)

# Build targets
all: qenex.kernel

qenex.kernel: $(KERNEL_OBJS)
	$(LD) $(LDFLAGS) -o $@ $^
	@echo "QENEX Universal Kernel built successfully"

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

# Install kernel
install: qenex.kernel
	cp qenex.kernel /boot/
	update-grub
	@echo "QENEX Kernel installed to /boot/"

# Clean build
clean:
	rm -f $(KERNEL_OBJS) qenex.kernel
	@echo "Build cleaned"

# Build documentation
docs:
	doxygen Doxyfile
	@echo "Documentation generated"

# Run tests
test:
	make -C tests/
	@echo "Kernel tests completed"

.PHONY: all install clean docs test