// SPDX-License-Identifier: Apache-2.0
package de.eibelucas.kiosksip;

import java.util.HashMap;
import java.util.Map;
import me.jxl.kiosk.plugins.KioskPlugin;
import me.jxl.kiosk.plugins.PluginHost;

public final class KioskSipPlugin implements KioskPlugin {
    private PluginHost host;
    private String gatewayUrl = "http://homeassistant.local:8088/";

    @Override
    public void start(PluginHost host, Map<String, Object> settings) {
        this.host = host;
        applySettings(settings);
        host.status("Bereit. Gateway: " + gatewayUrl, false);
    }

    @Override
    public void configure(Map<String, Object> settings) {
        applySettings(settings);
        if (host != null) host.status("Gateway aktualisiert: " + gatewayUrl, false);
    }

    @Override
    public void execute(String command, Map<String, Object> arguments) {
        if (!"openPhone".equals(command)) {
            throw new IllegalArgumentException("Unknown command: " + command);
        }
        Map<String, Object> args = new HashMap<>();
        args.put("url", gatewayUrl);
        host.executeCommand("showLinkPage", args, (ok, data, error) -> {
            if (!ok) host.status(error == null ? "Telefonseite konnte nicht geöffnet werden" : error, true);
        });
    }

    @Override
    public void onEvent(String event, Map<String, Object> payload) {
        // Reserved for future incoming-call/intercom synchronization.
    }

    @Override
    public void stop() {
        host = null;
    }

    private void applySettings(Map<String, Object> settings) {
        Object configured = settings == null ? null : settings.get("gatewayUrl");
        if (configured instanceof String && !((String) configured).trim().isEmpty()) {
            String candidate = ((String) configured).trim();
            if (!candidate.startsWith("http://") && !candidate.startsWith("https://")) {
                throw new IllegalArgumentException("Gateway URL must start with http:// or https://");
            }
            gatewayUrl = candidate;
        }
    }
}
