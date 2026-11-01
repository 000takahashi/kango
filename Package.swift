// swift-tools-version:5.9
import PackageDescription

// 勘合（kango）＝届いた連絡を「自分の契約台帳」と「会社の公式ドメイン」で照合する判定の部品。
// Swift Package Manager は、この設計図がリポジトリのいちばん上にある前提で読む。
// そのため設計図はここに置き、中身は swift/ に置いている。
// 外の部品には頼らない（ここに依存を足すと、勘合を使う全員にその部品が届く）。
let package = Package(
    name: "Kango",
    defaultLocalization: "ja",
    platforms: [.iOS(.v17), .macOS(.v13)],
    products: [.library(name: "Kango", targets: ["Kango"])],
    targets: [
        .target(
            name: "Kango",
            path: "swift/Sources/Kango",
            resources: [.process("Resources")]
        ),
        .testTarget(
            name: "KangoTests",
            dependencies: ["Kango"],
            path: "swift/Tests/KangoTests"
        ),
    ]
)
