# Code signing & notarization

DevFoundry's release workflow ([.github/workflows/release.yml](../.github/workflows/release.yml)) is
wired to produce **signed & notarized** installers — but signing requires **your own** developer
credentials. Nothing is (or can be) hardcoded; you add them as GitHub repository secrets.

## macOS (Developer ID + notarization)

Requires a paid **Apple Developer** account ($99/yr).

1. In Xcode or the Apple Developer portal, create a **Developer ID Application** certificate.
2. Export it from Keychain Access as a `.p12` (with a password), then base64-encode it:
   ```bash
   base64 -i DeveloperID.p12 | pbcopy
   ```
3. Create an **app-specific password** at appleid.apple.com (for notarization).
4. Add these **repository secrets** (Settings → Secrets and variables → Actions):

   | Secret | Value |
   |--------|-------|
   | `APPLE_CERTIFICATE` | the base64 `.p12` |
   | `APPLE_CERTIFICATE_PASSWORD` | the `.p12` password |
   | `APPLE_SIGNING_IDENTITY` | e.g. `Developer ID Application: Your Name (TEAMID)` |
   | `APPLE_ID` | your Apple ID email |
   | `APPLE_PASSWORD` | the app-specific password |
   | `APPLE_TEAM_ID` | your 10-char Team ID |

5. Tag a release (`git tag v0.2.0 && git push --tags`). The workflow signs, notarizes, and staples
   the `.app`/`.dmg`. Users then open it with no Gatekeeper warning.

## Windows (Authenticode)

Add a code-signing certificate and configure `tauri.conf.json` → `bundle.windows.certificateThumbprint`
(or use a cloud signing service). Without it, SmartScreen warns on first run.

## Local (unsigned) builds

`npm run tauri build` produces an **ad-hoc signed** app — fine for your own machine, but other users
see a Gatekeeper/SmartScreen warning. That's expected until the secrets above are set.

## Updater (optional)

For auto-updates (`tauri-plugin-updater`), generate a signing keypair
(`npm run tauri signer generate`) and add `TAURI_SIGNING_PRIVATE_KEY` +
`TAURI_SIGNING_PRIVATE_KEY_PASSWORD` as secrets.

---

**Why this can't be fully automated here:** the certificate and Apple credentials are yours and must
stay private. The pipeline is ready — it just needs those six secrets to produce a notarized build.
