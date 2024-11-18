
# Building Linphone SDK from source

### Clone https://gitlab.linphone.org/BC/public/linphone-sdk

### Update submodules

```
git submodule update --init --recursive
```

### Checkout the version you want

```
git checkout 5.3.95
```

## Follow Linphone SDK README's build dependencies section as needed, then build and package using the following steps.

### Prepare path to our SPM git dir, and the correct version tag

```
export PATH_TO_SPM_DIR=~/Git/linphone/spm
export LINPHONE_VERSION=$(git describe --tags --exact-match)
```

### Apply patches as needed

```
for p in ${PATH_TO_SPM_DIR}/*.patch; do echo $p; patch --strip=1 --forward --input $p; done
```

### Create cmake build dir

```
mkdir -p build/ && cd build/
```

### iOS cmake build steps, with an additional copy step at the end, this is a one-liner that can be re-run to re-build and copy

```
cmake .. -G Ninja --preset=ios-sdk -DCMAKE_BUILD_TYPE=Release -DENABLE_GPL_THIRD_PARTIES=NO -DENABLE_NON_FREE_CODECS=NO -DENABLE_VIDEO=NO -DENABLE_ADVANCED_IM=NO -DENABLE_DB_STORAGE=NO -DENABLE_VCARD=NO -DENABLE_MKV=NO -DENABLE_LDAP=NO -DENABLE_JPEG=NO -DENABLE_QRCODE=NO -DENABLE_FLEXIAPI=NO -DENABLE_LIME_X3DH=NO -DENABLE_GSM=NO -DENABLE_ILBC=NO -DENABLE_ISAC=NO \
&& cmake --build . --parallel 4 \
&& rm -rf linphone-sdk-ios-${LINPHONE_VERSION} \
&& unzip -d linphone-sdk-ios-${LINPHONE_VERSION} linphone-sdk-*.zip \
&& rm -rf ${PATH_TO_SPM_DIR}/XCFrameworks/* \
&& cp -vrf linphone-sdk-ios-${LINPHONE_VERSION}/linphone-sdk*/apple-darwin/XCFrameworks/ ${PATH_TO_SPM_DIR}/XCFrameworks/ \
&& cp -vrf linphone-sdk-ios-${LINPHONE_VERSION}/linphone-sdk*/apple-darwin/share/linphonesw/* ${PATH_TO_SPM_DIR}/Sources/linphonesw/ \
&& echo 'Success!'
```

### Android cmake build steps, the artifacts then need to be manually uploaded to Nexus

```
cmake .. -G Ninja --preset=android-sdk -DLINPHONESDK_PLATFORM=Android -DLINPHONESDK_ANDROID_ARCHS=arm64,armv7,x86,x86_64 -DCMAKE_BUILD_TYPE=Release -DENABLE_GPL_THIRD_PARTIES=NO -DENABLE_NON_FREE_CODECS=NO -DENABLE_VIDEO=NO -DENABLE_ADVANCED_IM=NO -DENABLE_DB_STORAGE=NO -DENABLE_VCARD=NO -DENABLE_MKV=NO -DENABLE_LDAP=NO -DENABLE_JPEG=NO -DENABLE_QRCODE=NO -DENABLE_FLEXIAPI=NO -DENABLE_LIME_X3DH=NO -DENABLE_GSM=NO -DENABLE_ILBC=NO -DENABLE_ISAC=NO \
&& cmake --build . --parallel 4
```

### Finally commit changes in the SPM repo and update Package.swift references as needed

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

# Linphone SPM source code notes

### LinphoneWrapper is the standard API wrapper copied from the SDK, no modifications done to it
[LinphoneWrapper.swift](Sources/linphonesw/LinphoneWrapper.swift)

### These contain Linphone's CallKit integration from [their app](https://gitlab.linphone.org/BC/public/linphone-iphone), and are modified for our calling stack
[CallManager.swift](Sources/linphonesw/CallManager.swift)
[ProviderDelegate.swift](Sources/linphonesw/ProviderDelegate.swift)
