// swift-tools-version:5.7
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
    name: "linphonesw",
    defaultLocalization: "en",
    platforms: [
        .iOS(.v14)
    ],
    products: [
        // Products define the executables and libraries a package produces, and make them visible to other packages.
        .library(name: "linphonesw", targets: ["linphonesw"])
    ],
    targets: [
        // Targets are the basic building blocks of a package. A target can define a module or a test suite.
        // Targets can depend on other targets in this package, and on products in packages this package depends on.

        .target(
            name: "linphonesw",
            dependencies: [
                "linphone",
                "bctoolbox-ios",
                "bctoolbox",
                "belr",
                "belle-sip",
                "mediastreamer2",
                "msamr",
                "mscodec2",
                "msopenh264",
                "mssilk",
                "ortp",
            ]
        ),
        .binaryTarget(
            name: "linphone",
            path: "XCFrameworks/linphone.xcframework"
        ),
        .binaryTarget(
            name: "bctoolbox-ios",
            path: "XCFrameworks/bctoolbox-ios.xcframework"
        ),
        .binaryTarget(
            name: "bctoolbox",
            path: "XCFrameworks/bctoolbox.xcframework"
        ),
        .binaryTarget(
            name: "belr",
            path: "XCFrameworks/belr.xcframework"
        ),
        .binaryTarget(
            name: "belle-sip",
            path: "XCFrameworks/belle-sip.xcframework"
        ),
        .binaryTarget(
            name: "mediastreamer2",
            path: "XCFrameworks/mediastreamer2.xcframework"
        ),
        .binaryTarget(
            name: "msamr",
            path: "XCFrameworks/msamr.xcframework"
        ),
        .binaryTarget(
            name: "mscodec2",
            path: "XCFrameworks/mscodec2.xcframework"
        ),
        .binaryTarget(
            name: "msopenh264",
            path: "XCFrameworks/msopenh264.xcframework"
        ),
        .binaryTarget(
            name: "mssilk",
            path: "XCFrameworks/mssilk.xcframework"
        ),
        .binaryTarget(
            name: "ortp",
            path: "XCFrameworks/ortp.xcframework"
        )
    ]
)
