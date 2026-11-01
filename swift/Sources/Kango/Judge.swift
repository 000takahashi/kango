import Foundation

/// 判定の結果。青でも「本物」「安全」とは言わない（割符が合った、まで）。
public struct Verdict: Equatable, Sendable {
    public enum Level: Int, Comparable, Codable, Sendable {
        case green = 0, amber, red
        public static func < (a: Level, b: Level) -> Bool { a.rawValue < b.rawValue }
    }

    public struct Reason: Equatable, Sendable {
        public let code: String
        public let text: String
    }

    public let level: Level
    public let reasons: [Reason]
    public let claimed: [String]
    public let hosts: [String]

    public var head: String {
        switch level {
        case .green: return "割符が合いました"
        case .amber: return "確かめきれません"
        case .red: return "割符が合いません。偽物の疑いが強いです"
        }
    }

    public var todo: String {
        switch level {
        case .green: return "念のため、リンクではなく公式アプリやいつものブックマークから開いて確かめてください。"
        case .amber: return "リンクは押さずに、公式アプリやいつものブックマークから開いて確かめてください。"
        case .red: return "リンクは押さないでください。入力してしまった時は、すぐにパスワードを変え、カード会社や銀行に連絡してください。"
        }
    }

    public struct Helpline: Hashable, Sendable {
        public let label: String
        public let tel: String
    }

    /// 迷った時の窓口（青では出さない）
    public var helplines: [Helpline] {
        level == .green ? [] : [.init(label: "警察相談専用電話", tel: "#9110"), .init(label: "消費者ホットライン", tel: "188")]
    }

    public static func == (a: Verdict, b: Verdict) -> Bool {
        a.level == b.level && a.reasons == b.reasons && a.claimed == b.claimed && a.hosts == b.hosts
    }
}

/// 勘合（割符の照合）。決定的・端末の中だけで動く。python/kango と同じ規則（SPEC.md）。
/// ★文章の上手さは見ない／リンク先へアクセスしない／文面を保存しない。
public enum Judge {
    static let shorteners: Set<String> = ["bit.ly", "t.co", "tinyurl.com", "is.gd", "x.gd", "t.ly", "cutt.ly", "ow.ly", "rebrand.ly"]

    /// 詐欺によくある言いまわし（言葉ひとつでは赤にしない＝黄まで）
    static let pressure: [(word: String, reason: String)] = [
        ("停止", "アカウントの停止で急がせる"), ("凍結", "凍結をちらつかせる"),
        ("24時間以内", "期限で急がせる"), ("本日中", "期限で急がせる"),
        ("支払い情報", "支払い情報を入力させようとする"), ("お支払い方法", "支払い方法を更新させようとする"),
        ("カード情報", "カード情報を求める"), ("暗証番号", "暗証番号を求める（正規の会社は聞きません）"),
        ("パスワード", "パスワードの入力を求める"), ("ギフトカード", "ギフトカードでの支払いを求める"),
        ("未納", "未納を理由に払わせる"), ("不在", "不在通知を装う"),
        ("ご本人確認", "本人確認を名目に入力させる"), ("異常なログイン", "不正ログインで不安をあおる"),
    ]

    /// 見た目が似た文字（amaz0n・rakut3n 等）を戻してから、似せた住所を探す
    static let lookalike: [Character: Character] = ["0": "o", "1": "l", "3": "e", "5": "s", "4": "a"]

    static let urlPattern = try! NSRegularExpression(pattern: #"https?://[^\s「」<>"'）)]+"#, options: [.caseInsensitive])
    static let hostPattern = try! NSRegularExpression(pattern: #"^https?://([^/?#:]+)"#, options: [.caseInsensitive])

    /// 電話番号＝0（または +81）で始まり、区切り（空白・かっこ・ハイフン類＝数字の間に3文字まで）を除いて10〜11桁（+81 の時は9〜10桁）。
    /// 前後に数字が続くもの（注文番号など）は数えない。番号が本物かは確かめられない＝黄まで。
    static let phonePattern = try! NSRegularExpression(pattern: #"(?<![0-9])(?:\+81[ ()\-‐−–ー]{0,3}|0)[1-9](?:[ ()\-‐−–ー]{0,3}[0-9]){8,9}(?![0-9])"#)

    static func norm(_ s: String) -> String { s.precomposedStringWithCompatibilityMapping.lowercased() }

    public static func host(of url: String) -> String? {
        let range = NSRange(url.startIndex..., in: url)
        guard let m = hostPattern.firstMatch(in: url, range: range),
              let r = Range(m.range(at: 1), in: url) else { return nil }
        var h = url[r].lowercased()
        while h.hasSuffix(".") { h.removeLast() }
        return h.isEmpty ? nil : h
    }

    public static func urls(in text: String) -> [String] {
        let t = text.precomposedStringWithCompatibilityMapping
        return urlPattern.matches(in: t, range: NSRange(t.startIndex..., in: t))
            .compactMap { Range($0.range, in: t).map { String(t[$0]) } }
    }

    /// リンクを除いた文面に、電話番号が書かれているか（リンクの中の数字は数えない）
    public static func hasPhoneNumber(_ text: String) -> Bool {
        let t = text.precomposedStringWithCompatibilityMapping
        let plain = urlPattern.stringByReplacingMatches(in: t, range: NSRange(t.startIndex..., in: t), withTemplate: " ")
        return phonePattern.firstMatch(in: plain, range: NSRange(plain.startIndex..., in: plain)) != nil
    }

    public static func isOfficial(_ host: String, _ brand: Brand) -> Bool {
        brand.domains.contains { host == $0 || host.hasSuffix("." + $0) }
    }

    /// 公式でない住所に、会社の名前（似せた文字も含む）が入っていれば その会社
    public static func mimicked(_ host: String, in brands: [Brand]) -> Brand? {
        let plain = String(host.map { lookalike[$0] ?? $0 })
        return brands.first { b in
            !isOfficial(host, b) && b.stems.contains { host.contains($0) || plain.contains($0) }
        }
    }

    public static func judge(text: String, ledger: Set<String>, brands: [Brand] = Catalog.bundled) -> Verdict {
        let low = norm(text)
        let claimed = brands.filter { b in b.words.contains { low.contains(norm($0)) } }
        let hosts = unique(urls(in: text).compactMap(host(of:)))
        var reasons: [Verdict.Reason] = []
        var level = Verdict.Level.green

        func say(_ code: String, _ text: String, _ l: Verdict.Level) {
            reasons.append(.init(code: code, text: text))
            level = max(level, l)
        }

        if claimed.isEmpty {
            say("no_claim", "どの会社を名乗っているか読み取れませんでした。", .amber)
        }
        for b in claimed where b.kind == .contract {
            if ledger.contains(b.id) {
                say("in_ledger", "「\(b.name)」はあなたの割符にあります。", .green)
            } else {
                say("not_in_ledger", "「\(b.name)」を名乗っていますが、あなたの割符（契約している会社）にありません。", .red)
            }
        }

        for h in hosts {
            if shorteners.contains(h) {
                say("shortener", "リンク（\(h)）は短縮URLで、行き先が見えません。", .amber)
                continue
            }
            if h.hasPrefix("xn--") || h.contains(".xn--") {
                say("idn", "リンク先「\(h)」は、見た目を似せやすい特殊な文字の住所です。", .red)
                continue
            }
            let owner = brands.first { isOfficial(h, $0) }
            if !claimed.isEmpty && !claimed.contains(where: { isOfficial(h, $0) }) {
                if let look = mimicked(h, in: claimed) {
                    say("mimic", "リンク先「\(h)」は「\(look.name)」に似せた住所ですが、公式の住所ではありません。", .red)
                } else {
                    say("off_domain", "リンク先「\(h)」は、名乗った会社の公式の住所ではありません。", .red)
                }
            } else if let owner {
                say("official", "リンク先「\(h)」は「\(owner.name)」の公式の住所と一致しました。", .green)
            } else if let look = mimicked(h, in: brands) {
                say("mimic", "リンク先「\(h)」は「\(look.name)」に似せた住所ですが、公式の住所ではありません。", .red)
            } else {
                say("unknown_domain", "リンク先「\(h)」は、登録された公式の住所ではありません。", .amber)
            }
        }

        if hasPhoneNumber(text) {
            say("phone", "電話番号が書かれています。この番号が本物かは確かめられません。電話する時は、公式サイトやカードの裏面など、自分で確かめた番号からかけてください。", .amber)
        }

        let tricks = unique(pressure.filter { low.contains($0.word) }.map(\.reason))
        if !tricks.isEmpty {
            say("pressure", "詐欺によくある言いまわし：" + tricks.joined(separator: "、") + "。", .amber)
        }

        return Verdict(level: level, reasons: reasons, claimed: claimed.map(\.id), hosts: hosts)
    }

    static func unique(_ xs: [String]) -> [String] {
        var seen = Set<String>()
        return xs.filter { seen.insert($0).inserted }
    }
}
