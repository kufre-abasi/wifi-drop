# Security policy

## Supported versions

Security fixes are applied to the latest version on the default branch.

## Local-network trust model

WiFi Drop is designed for trusted local networks. It uses an unencrypted local HTTP connection and a random session PIN embedded in the private link. It does not provide internet-facing authentication and should not be exposed through port forwarding, a public IP address, or an untrusted guest network.

Only files explicitly selected in the desktop app are available for phone download. Targeted files are shown only to the browser device selected in the desktop app. Device registration is session-local and contains a user-editable name, local IP address, browser user-agent, and last-seen time; it is not uploaded elsewhere. The phone interface does not enumerate the laptop's other files. Incomplete uploads remain hidden and are removed when the transfer is cancelled.

## Reporting a vulnerability

Please report security issues privately through GitHub's **Report a vulnerability** feature instead of opening a public issue. Include reproduction steps, affected versions, and expected impact.
