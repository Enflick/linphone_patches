
# Building Linphone SDK from source

### Clone https://gitlab.linphone.org/BC/public/linphone-sdk

### Update submodules

```
git submodule update --init --recursive
```

### Checkout the version you want

```
git checkout 5.4.85
```

# Opus 1.5 deep PLC / OSCE build (CALL-357)

Reproducible recipe for the 5.5.0-based build with Opus 1.5.2 deep PLC/OSCE and
decoder-complexity control. Patches for this stack live on the
`CALL-357-opus-15-testing` branch of this repo.

### Base

```
git checkout 5.5.0
git submodule update --init --recursive   # flaky; retry until all submodules sync
```

### Cherry-pick upstream Opus 1.5 support (from linphone-sdk master)

In order:

1. `b089673eb2dc7467622098168ea0aa3455b2a367` — "Allow setting the complexity of the
   opus decoder by setting the `_complexity` parameter in the recv fmtp of the opus
   payload."
2. `28d4ed9d750decbb4edbb6f23875a306ba7f750c` — "Update opus to v1.5.2 & activate OSCE
   (deep PLC and LACE/noLACE)." Also disables fixed point on mobile (OSCE needs float).
3. `9bfce4d5ac2755e64be76abcb01e7354c73f13df` — "Update opus submodule to fix build for
   Android armv7." This is upstream's adoption of our `opus_arm_dnn_rtcd_fix.patch`;
   once cherry-picked, skip that patch.

### Apply TN patches

Apply from `CALL-357-opus-15-testing`:
network_simulator_packet_loss, delay_ice_for_external_callback, disable_firebase_push,
disable_local_network_permission, expose_call_reconnect, ice_reuse_creds,
is_audio_session_active, remove_rings, revert_96de42ced (one hunk may need
hand-porting), rtp_payload_checks, run_loop_crash_fix, start_audio_unit_on_main_thread,
terminate_on_cancel, use_system_http_proxy, camera_and_data_sync_permission.

Skip — already upstream in 5.5.0 or superseded: cherry_pick_nat_policy_crash_fix,
cherry_pick_audio_focus_crash_fix, turn_end_hang_fix (superseded by upstream
non-blocking TLS handshake), opus_arm_dnn_rtcd_fix (in opus 4b8156b2 via cherry-pick 3
above), xcode_build_fixes (iOS toolchain file no longer exists).

### Behavioral gating

The stack is inert unless Opus is the negotiated codec AND the app opts in:

- Decoder complexity is read only by the Opus decoder (`msopus.c` fmtp handler for
  `_complexity`) and defaults to 0, so deep PLC/OSCE stays off unless the app sets
  `_complexity` on the opus payload's recv fmtp. `_`-prefixed params are stripped from
  outgoing SDP, so nothing leaks on the wire. Other codecs never see it.
- `linphone_core_enable_network_simulator_packet_loss()` (test harness only) does
  nothing unless explicitly called.
- The one unconditional change: the Opus 1.5.2 upgrade itself (float instead of fixed
  point on mobile) applies whenever opus encodes/decodes, regardless of complexity.

Then build with the Android cmake steps below and upload the AAR to Nexus.

## Follow Linphone SDK README's build dependencies section as needed, then build and package using the following steps.

### Prepare path to our SPM git dir, and the correct version tag

```
export PATH_TO_SPM_DIR=~/Git/linphone/spm
export LINPHONE_VERSION=$(git describe --tags --exact-match)
```

### Cleanup git state, then apply reverts and patches as needed

```
git co . && git submodule foreach 'git reset ; git checkout . ; git clean -fd'
git submodule update --init --recursive
for p in ${PATH_TO_SPM_DIR}/*.patch; do echo $p; patch --strip=1 --forward --input $p; done
```

### Create cmake build dir

```
mkdir -p build/ && cd build/
```

### iOS cmake build steps, with an additional copy step at the end, this is a one-liner that can be re-run to re-build and copy

Note: Linphone 5.2.x appears to need Xcode 15.4 for -mno-thumb, use `xcode-select --switch` or `xcodes` if needed to switch to 15.4

```
cmake .. -G Xcode --preset=ios-sdk -DCMAKE_BUILD_TYPE=RelWithDebInfo -DENABLE_GPL_THIRD_PARTIES=NO -DENABLE_NON_FREE_CODECS=NO -DENABLE_VIDEO=NO -DENABLE_ADVANCED_IM=NO -DENABLE_DB_STORAGE=NO -DENABLE_VCARD=NO -DENABLE_MKV=NO -DENABLE_LDAP=NO -DENABLE_JPEG=NO -DENABLE_QRCODE=NO -DENABLE_FLEXIAPI=NO -DENABLE_LIME_X3DH=NO -DENABLE_GSM=NO -DENABLE_ILBC=NO -DENABLE_ISAC=NO -DENABLE_DOC=NO -DENABLE_SWIFT_WRAPPER=NO \
&& cmake --build . --parallel 4 \
&& rm -rf linphone-sdk-ios-${LINPHONE_VERSION} \
&& unzip -d linphone-sdk-ios-${LINPHONE_VERSION} linphone-sdk-*.zip \
&& rm -rf ${PATH_TO_SPM_DIR}/XCFrameworks/* \
&& cp -vrf linphone-sdk-ios-${LINPHONE_VERSION}/linphone-sdk*/apple-darwin/XCFrameworks/ ${PATH_TO_SPM_DIR}/XCFrameworks/ \
&& echo 'Success!'
```

### (iOS Only) Commit iOS changes in the SPM repo and update Package.swift references as needed

## Upload dSYMS from the build folder

```
export DATADOG_API_KEY=<your-key-here>
npx @datadog/datadog-ci dsyms upload ./ios-arm64/lib/Debug/
```

### Android cmake build steps

Note: it is recommended to use NDK version 27 or later (ver. 25.2.x has a weird problem with OPUS audio quality).
v27 is needed for Android 16kb mode support, see: https://bugs.linphone.org/view.php?id=13926

```
cmake .. -G Ninja --preset=android-sdk -DLINPHONESDK_PLATFORM=Android -DLINPHONESDK_ANDROID_ARCHS=arm64,armv7,x86,x86_64 -DCMAKE_BUILD_TYPE=RelWithDebInfo -DENABLE_GPL_THIRD_PARTIES=NO -DENABLE_NON_FREE_CODECS=NO -DENABLE_VIDEO=NO -DENABLE_ADVANCED_IM=NO -DENABLE_DB_STORAGE=NO -DENABLE_VCARD=NO -DENABLE_MKV=NO -DENABLE_LDAP=NO -DENABLE_JPEG=NO -DENABLE_QRCODE=NO -DENABLE_FLEXIAPI=NO -DENABLE_LIME_X3DH=NO -DENABLE_GSM=NO -DENABLE_ILBC=NO -DENABLE_ISAC=NO \
&& cmake --build . --parallel 4
```

### (Android Only) Upload Android release and debug .aar to Maven

```
python $PATH_TO_SPM_DIR/upload_aar_to_nexus.py \
  --user USER --password PASS \
  --repository linphone-tn \
  --group-id org.linphone \
  --artifact-id linphone-sdk-android \
  --version $LINPHONE_VERSION-CUSTOM-VERISON-AND-TAG \
  --file maven_repository/org/linphone/linphone-sdk-android/5*/linphone-sdk-android*.aar

python $PATH_TO_SPM_DIR/upload_aar_to_nexus.py \
  --user USER --password PASS \
  --repository linphone-tn \
  --group-id org.linphone \
  --artifact-id linphone-sdk-android-debug \
  --version $LINPHONE_VERSION-CUSTOM-VERISON-AND-TAG \
  --file maven_repository/org/linphone/linphone-sdk-android-debug/5*/linphone-sdk-android*.aar
```

# Linphone prebuilt archives

This repo is based on: [linphone-sdk-ios-5.2.94.zip](https://download.linphone.org/releases/ios/linphone-sdk-ios-5.2.94.zip)

From: https://download.linphone.org/releases/ios/?C=M;O=D

For updating directly from a zip archive, use the unzip and copy command from above:

```
unzip -d linphone-sdk-ios-${LINPHONE_VERSION} linphone-sdk-ios-${LINPHONE_VERSION}.zip \
&& rm -rf ${PATH_TO_SPM_DIR}/XCFrameworks/* \
&& cp -vrf linphone-sdk-ios-${LINPHONE_VERSION}/linphone-sdk/apple-darwin/XCFrameworks/ ${PATH_TO_SPM_DIR}/XCFrameworks/ \
&& cp -vrf linphone-sdk-ios-${LINPHONE_VERSION}/linphone-sdk/apple-darwin/share/linphonesw/* ${PATH_TO_SPM_DIR}/Sources/linphonesw/
```

### Finally commit changes in the SPM repo and update Package.swift references as needed
### Important note! The XCFramework folder contains BINARY static library files and changes, per branch
### They should only updated to have the LATEST iOS binaries as the LAST commit, which was not done before.
### Otherwise the entire history of the binary changes will be uploaded, which can hit the Git 100MB limit.

# Linphone SPM source code notes

### LinphoneWrapper is the standard API wrapper copied from the SDK, no modifications done to it
[LinphoneWrapper.swift](Sources/linphonesw/LinphoneWrapper.swift)
