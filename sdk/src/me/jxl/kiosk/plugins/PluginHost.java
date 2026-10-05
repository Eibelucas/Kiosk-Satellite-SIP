// SPDX-License-Identifier: Apache-2.0
package me.jxl.kiosk.plugins;

import java.util.Map;

public interface PluginHost {
    interface CommandCallback {
        void onResult(boolean ok, Object data, String error);
    }

    default void executeCommand(String command, Map<String, Object> arguments, CommandCallback callback) {
        throw new UnsupportedOperationException("SDK 1 required");
    }

    default void status(String message, boolean error) {
        throw new UnsupportedOperationException("SDK 1 required");
    }
}
