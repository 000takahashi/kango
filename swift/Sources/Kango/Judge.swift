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
        /// この理由の色と、何についての理由か（リンク先の住所、または会社の id）。
        /// 行に印を付ける `Judge.marks` だけが使う（Python の judge の答えにも出さない）。
        let level: Level
        let target: String?

        init(code: String, text: String, level: Level, target: String? = nil) {
            self.code = code
            self.text = text
            self.level = level
            self.target = target
        }
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

    /// 乗っ取りの入口によくある頼みごと（顔認証・指紋・パスキーそのものではなく、本人に操作させる手口）。
    /// 言葉だけでは赤にしない＝黄まで。照合は正規化した文面（NFKC・小文字）に対して行う。
    static let takeover: [(pattern: NSRegularExpression, reason: String)] = [
        (#"(パスキー|顔認証|指紋認証|生体認証).{0,6}(再登録|再設定|作り直|登録し直|設定し直|登録をし直|設定をし直)"#,
         "パスキーや顔認証を作り直させようとする"),
        (#"(自撮り|セルフィー|顔写真(?!付)|顔の(写真|画像|動画)).{0,30}(身分証|免許証|マイナンバーカード|パスポート|在留カード|送信|送って|送付|アップロード)"#,
         "顔写真や身分証を送らせようとする"),
        (#"(身分証|免許証|マイナンバーカード|パスポート|在留カード).{0,30}(自撮り|セルフィー|顔写真(?!付)|顔の(写真|画像|動画))"#,
         "顔写真や身分証を送らせようとする"),
        (#"(アカウント|ログイン).{0,6}(復旧|復元|ロック解除|ロックを解除|制限解除|制限を解除)"#,
         "アカウントの復旧を名目に操作させる"),
        (#"(確認コード|認証コード|認証番号|ワンタイムパスワード|セキュリティコード|qrコード|二次元コード|[0-9]桁の(番号|コード|数字)).{0,20}(教えて|伝えて|読み上げて|お知らせください|返信して|読み取って|読みとって|スキャンして)"#,
         "確認コードやQRコードを渡させようとする"),
        (#"(遠隔操作|リモート操作|リモートサポート|画面共有|画面を共有|anydesk|teamviewer|quick ?support|クイックサポート|airdroid)"#,
         "遠隔操作や画面共有をさせようとする"),
    ].map { (try! NSRegularExpression(pattern: $0.0), $0.1) }

    /// 見た目が似た文字（amaz0n・rakut3n 等）を戻してから、似せた住所を探す
    static let lookalike: [Character: Character] = ["0": "o", "1": "l", "3": "e", "5": "s", "4": "a"]

    /// リンク＝ http: か https: のあとに / か \ が続く文字の並び（ブラウザは \ も / とみなし、/ が1つでも開く）。
    /// 空白・かぎかっこ・山かっこ・引用符・閉じかっこ・読点「、」で終わる。
    static let urlPattern = try! NSRegularExpression(pattern: #"https?:[/\\]+[^\s「」『』【】<>"'）)、]+"#, options: [.caseInsensitive])
    /// リンクの「住所の部分」（最初の / \ ? # まで）
    static let authorityPattern = try! NSRegularExpression(pattern: #"^https?:[/\\]+([^/\\?#]*)"#, options: [.caseInsensitive])
    /// 見た目の「住所の部分」（\ を区切りと思わずに読んだ時。ここに @ や \ があれば見せかけ）
    static let shownPattern = try! NSRegularExpression(pattern: #"^https?:[/\\]+([^/?#]*)"#, options: [.caseInsensitive])
    /// https:// の無いリンク（rakuten-card-login.com/abc など。メッセージアプリはこれも押せるリンクにする）。
    /// 英数字とハイフンの並びを . でつなぎ、最後が英字2〜24文字。前後に英数字や @ が付くもの（メールアドレスなど）は数えない。
    static let barePattern = try! NSRegularExpression(pattern: #"(?<![a-z0-9@._%+\-])((?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24})(?![a-z0-9\-@])(?:[/?#][^\s「」『』【】<>"'）)、]*)?"#, options: [.caseInsensitive])
    /// ファイル名（meisai.pdf など）は住所として数えない（どれもトップレベルドメインではない）
    static let fileExtensions: Set<String> = ["pdf", "html", "htm", "jpg", "jpeg", "png", "gif", "txt", "csv", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "js", "css", "json", "xml", "php", "exe", "apk"]
    /// 住所にふつう使う文字（英小文字・数字・. ・-）。これ以外を含む住所＝見た目を似せる手口か、壊れた住所
    static let hostCharsPattern = try! NSRegularExpression(pattern: #"^[a-z0-9.\-]+$"#)

    /// 電話番号＝0（または +81）で始まり、区切り（空白・かっこ・ハイフン類＝数字の間に3文字まで）を除いて10〜11桁（+81 の時は9〜10桁）。
    /// 前後に数字が続くもの（注文番号など）は数えない。番号が本物かは確かめられない＝黄まで。
    static let phonePattern = try! NSRegularExpression(pattern: #"(?<![0-9])(?:\+81[ ()\-‐−–ー]{0,3}|0)[1-9](?:[ ()\-‐−–ー]{0,3}[0-9]){8,9}(?![0-9])"#)

    static func norm(_ s: String) -> String { s.precomposedStringWithCompatibilityMapping.lowercased() }

    static func authority(of url: String, _ pattern: NSRegularExpression) -> String? {
        let range = NSRange(url.startIndex..., in: url)
        guard let m = pattern.firstMatch(in: url, range: range),
              let r = Range(m.range(at: 1), in: url) else { return nil }
        return String(url[r])
    }

    /// リンクの本当の行き先の住所（ホスト名）。ブラウザと同じ読み方をする：
    /// \ は / と同じ・@ より前（利用者名とパスワード）は住所ではない・: の後ろは番号（ポート）・「。」は「.」と同じ。
    public static func host(of url: String) -> String? {
        guard let auth = authority(of: url, authorityPattern) else { return nil }
        var h = auth.components(separatedBy: "@").last ?? ""
        h = h.hasPrefix("[") ? (h.components(separatedBy: "]").first ?? "") + "]" : (h.components(separatedBy: ":").first ?? "")
        h = h.replacingOccurrences(of: "。", with: ".").lowercased()
        while h.hasSuffix(".") { h.removeLast() }
        return h.isEmpty ? nil : h
    }

    /// 文面を、リンク・https:// の無いリンクの住所・それ以外の文字（電話番号を探す所）に分ける
    static func scan(_ text: String) -> (urls: [String], bare: [String], plain: String) {
        let t = text.precomposedStringWithCompatibilityMapping
        let urls = urlPattern.matches(in: t, range: NSRange(t.startIndex..., in: t))
            .compactMap { Range($0.range, in: t).map { String(t[$0]) } }
        let rest = urlPattern.stringByReplacingMatches(in: t, range: NSRange(t.startIndex..., in: t), withTemplate: " ")
        let bare = barePattern.matches(in: rest, range: NSRange(rest.startIndex..., in: rest))
            .compactMap { Range($0.range(at: 1), in: rest).map { String(rest[$0]).lowercased() } }
            .filter { !fileExtensions.contains($0.components(separatedBy: ".").last ?? "") }
        let plain = barePattern.stringByReplacingMatches(in: rest, range: NSRange(rest.startIndex..., in: rest), withTemplate: " ")
        return (urls, bare, plain)
    }

    public static func urls(in text: String) -> [String] { scan(text).urls }

    /// リンク（https:// の無いものも）を除いた文面に、電話番号が書かれているか（リンクの中の数字は数えない）
    public static func hasPhoneNumber(_ text: String) -> Bool {
        let plain = scan(text).plain
        return phonePattern.firstMatch(in: plain, range: NSRange(plain.startIndex..., in: plain)) != nil
    }

    static func hasOnlyHostChars(_ h: String) -> Bool {
        hostCharsPattern.firstMatch(in: h, range: NSRange(h.startIndex..., in: h)) != nil
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
        let found = scan(text)
        let hosts = unique(found.urls.compactMap(host(of:)) + found.bare)
        var reasons: [Verdict.Reason] = []
        var level = Verdict.Level.green

        func say(_ code: String, _ text: String, _ l: Verdict.Level, _ target: String? = nil) {
            reasons.append(.init(code: code, text: text, level: l, target: target))
            level = max(level, l)
        }

        if claimed.isEmpty {
            say("no_claim", "どの会社を名乗っているか読み取れませんでした。", .amber)
        }
        for b in claimed where b.kind == .contract {
            if ledger.contains(b.id) {
                say("in_ledger", "「\(b.name)」はあなたの割符にあります。", .green, b.id)
            } else {
                say("not_in_ledger", "「\(b.name)」を名乗っていますが、あなたの割符（契約している会社）にありません。", .red, b.id)
            }
        }

        // 「@」や「\」で本当の行き先をごまかす書き方（https://本物の住所@偽の住所/・https://偽の住所\@本物の住所/）
        let tricked = unique(found.urls.filter { u in
            (authority(of: u, shownPattern) ?? "").contains { $0 == "@" || $0 == "\\" }
        }.compactMap(host(of:)))
        for h in tricked {
            say("disguised", "リンクの住所に「@」や「\\」を使った見せかけがあります。本当の行き先は「\(h)」です。", .red, h)
        }

        for h in hosts {
            if shorteners.contains(h) {
                say("shortener", "リンク（\(h)）は短縮URLで、行き先が見えません。", .amber, h)
                continue
            }
            if h.hasPrefix("xn--") || h.contains(".xn--") || !hasOnlyHostChars(h) {
                say("idn", "リンク先「\(h)」は、ふつうの住所には使わない文字を含んでいます。見た目を似せる手口に使われます。", .red, h)
                continue
            }
            let owner = brands.first { isOfficial(h, $0) }
            if !claimed.isEmpty && !claimed.contains(where: { isOfficial(h, $0) }) {
                if let look = mimicked(h, in: claimed) {
                    say("mimic", "リンク先「\(h)」は「\(look.name)」に似せた住所ですが、公式の住所ではありません。", .red, h)
                } else {
                    say("off_domain", "リンク先「\(h)」は、名乗った会社の公式の住所ではありません。", .red, h)
                }
            } else if let owner {
                say("official", "リンク先「\(h)」は「\(owner.name)」の公式の住所と一致しました。", .green, h)
            } else if let look = mimicked(h, in: brands) {
                say("mimic", "リンク先「\(h)」は「\(look.name)」に似せた住所ですが、公式の住所ではありません。", .red, h)
            } else {
                say("unknown_domain", "リンク先「\(h)」は、登録された公式の住所ではありません。", .amber, h)
            }
        }

        // リンク（https:// の無いものも）の中の数字は数えない（住所はリンクとして照合済み）
        if phonePattern.firstMatch(in: found.plain, range: NSRange(found.plain.startIndex..., in: found.plain)) != nil {
            say("phone", "電話番号が書かれています。この番号が本物かは確かめられません。電話する時は、公式サイトやカードの裏面など、自分で確かめた番号からかけてください。", .amber)
        }

        let tricks = unique(pressure.filter { low.contains($0.word) }.map(\.reason))
        if !tricks.isEmpty {
            say("pressure", "詐欺によくある言いまわし：" + tricks.joined(separator: "、") + "。", .amber)
        }

        let asks = unique(takeover.filter {
            $0.pattern.firstMatch(in: low, range: NSRange(low.startIndex..., in: low)) != nil
        }.map(\.reason))
        if !asks.isEmpty {
            say("takeover", "乗っ取りの入口によくある頼みごと：" + asks.joined(separator: "、") + "。"
                + "本物の会社は、ふつうメールやSMSのリンク・電話でこれを頼みません。公式アプリから自分で確かめてください。", .amber)
        }

        // 何ひとつ照らし合わせられなかった（配送・郵便・国税庁を名乗り、リンクが無い等）＝青にしない。
        // 青は、何か1つでも割符が合った時（in_ledger・official）だけ。
        if reasons.isEmpty {
            say("nothing_to_check", "割符（契約している会社）や公式の住所へのリンクなど、照らし合わせられるものがありませんでした。", .amber)
        }

        return Verdict(level: level, reasons: reasons, claimed: claimed.map(\.id), hosts: hosts)
    }

    static func unique(_ xs: [String]) -> [String] {
        var seen = Set<String>()
        return xs.filter { seen.insert($0).inserted }
    }
}
