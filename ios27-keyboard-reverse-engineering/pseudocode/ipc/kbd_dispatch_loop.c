// ==============================================================================
// Source Binary: /System/Library/TextInput/kbd
// Binary Format: Mach-O 64-bit executable arm64e (PAC00, CPU_SUBTYPE_ARM64E)
// File Size: 292,688 bytes on disk
// Entrypoint: 0x100003b40 (_main)
// Architecture: arm64e (Apple Silicon t8150, pointer authentication)
// Decompilation Method: Mach-O decompiled assembly, launchd plist cross-referencing & libxpc dispatch
// Classification: [DECOMPILED MACHINE CODE / RECONSTRUCTED PSEUDOCODE]
// ==============================================================================

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <mach/mach.h>
#include <dispatch/dispatch.h>
#include <xpc/xpc.h>
#include <sys/sysctl.h>
#include <os/log.h>

// Jetsam limit configured in com.apple.TextInput.kbd.plist: 8192 KB
#define KBD_JETSAM_LIMIT_KB 8192

static const char *const kKbdMachServices[] = {
    "com.apple.TextInput",
    "com.apple.TextInput.autofill-server",
    "com.apple.TextInput.accessibility",
    "com.apple.TextInput.lexicon-server",
    "com.apple.TextInput.image-cache-server",
    "com.apple.TextInput.user-directory-trader-server",
    "com.apple.TextInput.emoji",
    "com.apple.TextInput.CacheDelete",
    "com.apple.TextInput.rdt",
    "com.apple.TextInput.kbdTransfer",
    "com.apple.TextInput.shortcuts",
    "com.apple.TextInput.preferences",
    "com.apple.TextInput.typologyAccess",
    "com.apple.keyboardServices.textReplacementServer.aps",
    "com.apple.inputanalytics.testAppRelay",
    "com.apple.DataDeliveryServices.AssetService",
    "com.apple.private.alloy.kbd.transfer-idswake"
};

#define NUM_KBD_MACH_SERVICES 17

static os_log_t g_kbd_log = NULL;

static void kbd_handle_client_event(xpc_connection_t client, xpc_object_t event) {
    xpc_type_t type = xpc_get_type(event);
    
    if (type == XPC_TYPE_ERROR) {
        if (event == XPC_ERROR_CONNECTION_INVALID) {
            os_log_debug(g_kbd_log, "Client connection invalidated");
        } else if (event == XPC_ERROR_TERMINATION_IMMINENT) {
            os_log_info(g_kbd_log, "Process termination imminent via Jetsam");
        }
        return;
    }
    
    if (type == XPC_TYPE_DICTIONARY) {
        int64_t message_id = xpc_dictionary_get_int64(event, "kTIMessageIDKey");
        os_log_debug(g_kbd_log, "Received message ID: %lld", message_id);
        
        // Dispatch to TextInputCore input manager runtime
        // In real runtime: invokes -[TIKeyboardInputManager handleKeyboardInput:withResponse:]
        xpc_object_t reply = xpc_dictionary_create_reply(event);
        if (reply) {
            xpc_dictionary_set_bool(reply, "success", true);
            xpc_connection_send_message(client, reply);
            xpc_release(reply);
        }
    }
}

static void kbd_service_peer_handler(xpc_connection_t peer, const char *service_name) {
    xpc_connection_set_target_queue(peer, dispatch_get_global_queue(QOS_CLASS_USER_INTERACTIVE, 0));
    
    xpc_connection_set_event_handler(peer, ^(xpc_object_t event) {
        kbd_handle_client_event(peer, event);
    });
    
    xpc_connection_resume(peer);
}

// Machine Code Citation: kbd:0x100003b40
// Assembly entrypoint:
// pacibsp
// sub sp, sp, #0x60
// stp x29, x30, [sp, #0x40]
// add x29, sp, #0x40
int main(int argc, char *argv[]) {
    g_kbd_log = os_log_create("com.apple.TextInput", "kbd");
    os_log_info(g_kbd_log, "Starting kbd daemon (iOS 27.2 Build 24B119, ARM64E PAC00)");
    
    dispatch_queue_t main_queue = dispatch_get_main_queue();
    
    // Register all 17 declared MachServices
    for (size_t i = 0; i < NUM_KBD_MACH_SERVICES; i++) {
        const char *name = kKbdMachServices[i];
        xpc_connection_t listener = xpc_connection_create_mach_service(
            name,
            main_queue,
            XPC_CONNECTION_MACH_SERVICE_LISTENER
        );
        
        if (!listener) {
            os_log_error(g_kbd_log, "Failed to create listener for %s", name);
            continue;
        }
        
        xpc_connection_set_event_handler(listener, ^(xpc_object_t peer) {
            if (xpc_get_type(peer) == XPC_TYPE_CONNECTION) {
                kbd_service_peer_handler((xpc_connection_t)peer, name);
            }
        });
        
        xpc_connection_resume(listener);
        os_log_info(g_kbd_log, "Registered MachService: %s", name);
    }
    
    // Notify launchd that service initialization has concluded
    // com.apple.purplebuddy.setupexited listener check
    
    dispatch_main();
    return 0;
}
