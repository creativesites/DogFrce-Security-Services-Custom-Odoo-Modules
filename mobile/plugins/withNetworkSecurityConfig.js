const { withAndroidManifest, withDangerousMod } = require('@expo/config-plugins');
const path = require('path');
const fs = require('fs');

// Generates android/app/src/main/res/xml/network_security_config.xml and
// registers it on the <application> element so cleartext HTTP traffic is
// permitted in release builds. This is more reliable than the
// android.usesCleartextTraffic app.json flag, which can be silently
// overridden when another plugin also writes networkSecurityConfig.
const withNetworkSecurityConfig = (config) => {
  config = withAndroidManifest(config, (config) => {
    const app = config.modResults.manifest.application[0];
    app.$['android:networkSecurityConfig'] = '@xml/network_security_config';
    return config;
  });

  config = withDangerousMod(config, [
    'android',
    (config) => {
      const xmlDir = path.join(
        config.modRequest.platformProjectRoot,
        'app/src/main/res/xml'
      );
      if (!fs.existsSync(xmlDir)) {
        fs.mkdirSync(xmlDir, { recursive: true });
      }
      fs.writeFileSync(
        path.join(xmlDir, 'network_security_config.xml'),
        [
          '<?xml version="1.0" encoding="utf-8"?>',
          '<network-security-config>',
          '  <!-- Allow cleartext (HTTP) traffic for the on-premise Odoo server. -->',
          '  <!-- Remove this when the server is moved to HTTPS.               -->',
          '  <base-config cleartextTrafficPermitted="true">',
          '    <trust-anchors>',
          '      <certificates src="system" />',
          '    </trust-anchors>',
          '  </base-config>',
          '</network-security-config>',
        ].join('\n')
      );
      return config;
    },
  ]);

  return config;
};

module.exports = withNetworkSecurityConfig;
