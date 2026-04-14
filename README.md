
# Building Linphone SDK from source

### Clone https://gitlab.linphone.org/BC/public/linphone-sdk

### Update submodules

```
git submodule update --init --recursive
```

### Checkout the version you want

```
git checkout 5.4.105
```

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
cmake .. -G Ninja --preset=ios-sdk -DCMAKE_BUILD_TYPE=RelWithDebInfo -DENABLE_GPL_THIRD_PARTIES=NO -DENABLE_NON_FREE_CODECS=NO -DENABLE_VIDEO=NO -DENABLE_ADVANCED_IM=NO -DENABLE_DB_STORAGE=NO -DENABLE_VCARD=NO -DENABLE_MKV=NO -DENABLE_LDAP=NO -DENABLE_JPEG=NO -DENABLE_QRCODE=NO -DENABLE_FLEXIAPI=NO -DENABLE_LIME_X3DH=NO -DENABLE_GSM=NO -DENABLE_ILBC=NO -DENABLE_ISAC=NO \
&& cmake --build . --parallel 4 \
&& rm -rf linphone-sdk-ios-${LINPHONE_VERSION} \
&& unzip -d linphone-sdk-ios-${LINPHONE_VERSION} linphone-sdk-*.zip \
&& rm -rf ${PATH_TO_SPM_DIR}/XCFrameworks/* \
&& cp -vrf linphone-sdk-ios-${LINPHONE_VERSION}/linphone-sdk*/apple-darwin/share/linphonesw/* ${PATH_TO_SPM_DIR}/Sources/linphonesw/ \
&& cp -vrf linphone-sdk-ios-${LINPHONE_VERSION}/linphone-sdk*/apple-darwin/XCFrameworks/ ${PATH_TO_SPM_DIR}/XCFrameworks/ \
&& pushd ${PATH_TO_SPM_DIR}/XCFrameworks/ \
&& find . | grep 'framework\.dSYM\|dSYMs' | xargs -I{} rm -rf {} \
&& popd \
&& echo 'Success!'
```

## Upload dSYM folders from the original build (they are excluded from the SPM repo for size reasons)

```
export DATADOG_API_KEY=<your-key-here>
npx @datadog/datadog-ci dsyms upload ./linphone-sdk-novideo/ios-arm64/Frameworks/
```

### Android cmake build steps, the artifacts then need to be manually uploaded to Nexus

Note: it is recommended to use NDK version 27 or later (ver. 25.2.x has a weird problem with OPUS audio quality).
v27 is needed for Android 16kb mode support, see: https://bugs.linphone.org/view.php?id=13926

```
cmake .. -G Ninja --preset=android-sdk -DLINPHONESDK_PLATFORM=Android -DLINPHONESDK_ANDROID_ARCHS=arm64,armv7,x86,x86_64 -DCMAKE_BUILD_TYPE=RelWithDebInfo -DENABLE_GPL_THIRD_PARTIES=NO -DENABLE_NON_FREE_CODECS=NO -DENABLE_VIDEO=NO -DENABLE_ADVANCED_IM=NO -DENABLE_DB_STORAGE=NO -DENABLE_VCARD=NO -DENABLE_MKV=NO -DENABLE_LDAP=NO -DENABLE_JPEG=NO -DENABLE_QRCODE=NO -DENABLE_FLEXIAPI=NO -DENABLE_LIME_X3DH=NO -DENABLE_GSM=NO -DENABLE_ILBC=NO -DENABLE_ISAC=NO \
&& cmake --build . --parallel 4
```

### Finally commit changes in the SPM repo and update Package.swift references as needed.
### Important note! The XCFramework folder contains BINARY static library files and changes, per branch
### They should only updated to have the LATEST iOS binaries as the LAST commit, which was not done before.
### Otherwise the entire history of the binary changes will be uploaded, which can hit the Git 100MB limit.

# Linphone SPM source code notes

### LinphoneWrapper is the standard API wrapper copied from the SDK, no modifications done to it
[LinphoneWrapper.swift](Sources/linphonesw/LinphoneWrapper.swift)
