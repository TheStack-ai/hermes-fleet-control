// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "HermesFleetControl",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "HermesFleetControl", targets: ["HermesFleetControl"])
    ],
    targets: [
        .executableTarget(name: "HermesFleetControl")
    ]
)
