CC ?= gcc
CFLAGS ?= -Wall -Wextra -std=c11 -O2
INCLUDES = -I../include -I../devices -I../firmware -I../../gpu/driver -I../../silenus/driver -I../../ave/include

SRCS = apple_a19_emulation_runner.c \
       ../devices/apple_aic.c \
       ../devices/apple_ascwrap.c \
       ../devices/apple_dart.c \
       ../devices/apple_agx_direct.c \
       ../devices/apple_silenus_dma.c \
       ../devices/apple_prores_hw.c \
       ../devices/apple_tightbeam_ipc.c \
       ../firmware/stub_rtkit_core.c

TARGET = apple_a19_emulation_runner

all: $(TARGET)

$(TARGET): $(SRCS)
	$(CC) $(CFLAGS) $(INCLUDES) -o $@ $(SRCS)

run: $(TARGET)
	./$(TARGET)

clean:
	rm -f $(TARGET) *.o

.PHONY: all run clean
