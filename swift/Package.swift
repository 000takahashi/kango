// swift-tools-version:5.9
import PackageDescription

// 勘合（kango）＝届いた連絡を「自分の契約台帳」と「会社の公式ドメイン」で照合する判定の部品。
let package = Package(
    name: "Kango",
    defaultLocalization: "ja",
    platforms: [.iOS(.v17), .macOS(.v13)],
    products: [.library(name: "Kango", targets: ["Kango"])],
    targets: [
        .target(name: "Kango", resources: [.process("Resources")]),
        .testTarget(name: "KangoTests", dependencies: ["Kango"]),
    ]
)
