import Foundation

enum FleetStatus: String, Codable {
    case healthy
    case degradedBackoff = "degraded_backoff"
    case busy
    case stopped
    case unknown
    case unclassified
    case inactive
    case ignored

    var symbolName: String {
        switch self {
        case .healthy: return "checkmark.seal.fill"
        case .degradedBackoff: return "exclamationmark.triangle.fill"
        case .busy: return "clock.badge"
        case .stopped: return "xmark.octagon.fill"
        case .unknown: return "questionmark.diamond.fill"
        case .unclassified: return "questionmark.folder.fill"
        case .inactive: return "pause.circle.fill"
        case .ignored: return "eye.slash.fill"
        }
    }

    var shortLabel: String {
        switch self {
        case .healthy: return "정상"
        case .degradedBackoff: return "재연결 대기"
        case .busy: return "작업 중"
        case .stopped: return "오프라인"
        case .unknown: return "확인 필요"
        case .unclassified: return "미분류"
        case .inactive: return "비활성"
        case .ignored: return "숨김"
        }
    }
}

struct FleetSnapshot: Codable {
    let ok: Bool
    let generatedAt: String
    let network: NetworkSnapshot
    let authHealth: AuthHealthSnapshot?
    let audit: AuditSnapshot?
    let servers: [FleetServer]

    enum CodingKeys: String, CodingKey {
        case ok
        case generatedAt = "generated_at"
        case network
        case authHealth = "auth_health"
        case audit
        case servers
    }

    var headline: String {
        if servers.isEmpty {
            return "Hermes 프로필 없음 · Setup needed"
        }
        let problemCount = servers.reduce(0) { partial, server in
            partial + server.summary.degraded + server.summary.stopped + server.summary.unknown
        }
        if problemCount == 0 && reloginCount == 0 && unclassifiedCount == 0 {
            return "전체 정상 · All systems ready"
        }
        if problemCount == 0 {
            if unclassifiedCount > 0 { return "Gateway 정상 · 미분류 \(unclassifiedCount)개" }
            return "Gateway 정상 · 인증 \(reloginCount)개 확인"
        }
        return "확인 필요 · \(problemCount)개 프로필"
    }

    var readyCount: Int {
        servers.reduce(0) { $0 + $1.summary.healthy }
    }

    var attentionCount: Int {
        servers.reduce(0) { $0 + $1.summary.degraded + $1.summary.stopped + $1.summary.unknown }
    }

    var unclassifiedCount: Int {
        servers.reduce(0) { $0 + $1.summary.unclassifiedCount }
    }

    var reloginCount: Int {
        servers.flatMap { $0.profiles }.filter { $0.auth?.reloginRequired == true }.count
    }

    var hasAttention: Bool {
        attentionCount > 0 || reloginCount > 0
    }

    var priorityProfiles: [FleetProfile] {
        servers.flatMap { $0.profiles }.filter { profile in
            profile.auth?.reloginRequired == true || {
                switch profile.status {
                case .degradedBackoff, .stopped, .unknown:
                    return true
                case .healthy, .busy, .unclassified, .inactive, .ignored:
                    return false
                }
            }()
        }
    }

    var attentionProfiles: [FleetProfile] {
        servers.flatMap { $0.profiles }.filter { profile in
            switch profile.status {
            case .degradedBackoff, .stopped, .unknown:
                return true
            case .healthy, .busy, .unclassified, .inactive, .ignored:
                return false
            }
        }
    }

    var classificationProfiles: [FleetProfile] {
        servers.flatMap { $0.profiles }.filter { profile in
            switch profile.status {
            case .unclassified, .inactive:
                return true
            case .healthy, .degradedBackoff, .busy, .stopped, .unknown, .ignored:
                return false
            }
        }
    }

    var attentionProfileKeys: Set<String> {
        Set(priorityProfiles.map { $0.profile })
    }
}

struct NetworkSnapshot: Codable {
    let skipped: Bool?
    let discordDnsOk: Bool?
    let discordTcpOk: Bool?

    enum CodingKeys: String, CodingKey {
        case skipped
        case discordDnsOk = "discord_dns_ok"
        case discordTcpOk = "discord_tcp_ok"
    }
}

struct AuthHealthSnapshot: Codable {
    let metadataOnly: Bool
    let codexOpenAI: CodexAuthHealth?
    let providers: [String: EnvProviderHealth]?

    enum CodingKeys: String, CodingKey {
        case metadataOnly = "metadata_only"
        case codexOpenAI = "codex_openai"
        case providers
    }

    var menuLine: String {
        guard let codexOpenAI else { return "Codex 인증 · unknown" }
        let providerText: String
        if let providers {
            let present = providers.values.filter { $0.keyPresent }.count
            providerText = " · providers \(present)/\(providers.count)"
        } else {
            providerText = ""
        }
        return "Codex 인증 · \(codexOpenAI.status) · token \(codexOpenAI.tokensPresent ? "있음" : "없음") · refresh \(codexOpenAI.lastRefreshPresent ? "있음" : "없음")\(providerText)"
    }
}

struct EnvProviderHealth: Codable {
    let provider: String
    let status: String
    let keyPresent: Bool
    let metadataOnly: Bool

    enum CodingKeys: String, CodingKey {
        case provider
        case status
        case keyPresent = "key_present"
        case metadataOnly = "metadata_only"
    }
}

struct CodexAuthHealth: Codable {
    let provider: String
    let status: String
    let authModePresent: Bool
    let tokensPresent: Bool
    let apiKeyPresent: Bool
    let lastRefreshPresent: Bool
    let metadataOnly: Bool

    enum CodingKeys: String, CodingKey {
        case provider
        case status
        case authModePresent = "auth_mode_present"
        case tokensPresent = "tokens_present"
        case apiKeyPresent = "api_key_present"
        case lastRefreshPresent = "last_refresh_present"
        case metadataOnly = "metadata_only"
    }
}

struct AuditSnapshot: Codable {
    let path: String
    let lastActions: [AuditAction]

    enum CodingKeys: String, CodingKey {
        case path
        case lastActions = "last_actions"
    }

    var latestLine: String? {
        lastActions.first?.menuLine
    }
}

struct AuditAction: Codable, Identifiable {
    let ts: String?
    let event: String?
    let action: String?
    let group: String?
    let targets: [String]?
    let dryRun: Bool?
    let degradedOnly: Bool?
    let ok: Bool?
    let message: String?

    var id: String { "\(ts ?? "unknown")-\(action ?? "action")-\(group ?? "scope")" }

    enum CodingKeys: String, CodingKey {
        case ts
        case event
        case action
        case group
        case targets
        case dryRun = "dry_run"
        case degradedOnly = "degraded_only"
        case ok
        case message
    }

    var menuLine: String {
        let scope = group ?? "profile"
        let targetText = (targets ?? []).isEmpty ? "no targets" : (targets ?? []).joined(separator: ", ")
        let liveText = dryRun == true ? "dry-run" : "live"
        let resultText = ok == false ? "failed" : "done"
        return "최근 실행 · \(liveText) · \(action ?? "action") · \(scope) · \(targetText) · \(resultText)"
    }
}

struct FleetServer: Codable, Identifiable {
    let key: String
    let display: String
    let summary: ServerSummary
    let profiles: [FleetProfile]

    var id: String { key }

    var menuTitle: String {
        display
    }
}

struct ServerSummary: Codable {
    let healthy: Int
    let degraded: Int
    let stopped: Int
    let busy: Int
    let unknown: Int
    let unclassified: Int?
    let inactive: Int?
    let ignored: Int?

    var unclassifiedCount: Int { unclassified ?? 0 }
    var inactiveCount: Int { inactive ?? 0 }
    var ignoredCount: Int { ignored ?? 0 }

    var isHealthy: Bool {
        degraded == 0 && stopped == 0 && unknown == 0 && unclassifiedCount == 0
    }

    var symbolName: String {
        if stopped > 0 { return "xmark.octagon.fill" }
        if degraded > 0 || unknown > 0 || unclassifiedCount > 0 { return "exclamationmark.triangle.fill" }
        if busy > 0 { return "clock.badge" }
        return "checkmark.seal.fill"
    }

    var compactLine: String {
        "정상 \(healthy) · 주의 \(degraded) · 오프라인 \(stopped) · 작업중 \(busy) · 미확인 \(unknown) · 미분류 \(unclassifiedCount) · 비활성 \(inactiveCount)"
    }

    var premiumLine: String {
        if isHealthy { return "모든 프로필 정상" }
        if degraded + stopped + unknown == 0 {
            return "정상 \(healthy) · 미분류 \(unclassifiedCount) · 비활성 \(inactiveCount)"
        }
        return "정상 \(healthy) · 조치필요 \(degraded + stopped + unknown) · 작업중 \(busy)"
    }
}

struct FleetProfile: Codable, Identifiable {
    let profile: String
    let display: String?
    let status: FleetStatus
    let activeAgents: Int
    let safeActions: [String]
    let lastSignal: String
    let auth: ProfileAuthHealth?

    var id: String { profile }

    var menuLine: String {
        let base = "\(display ?? profile) · \(status.shortLabel) · active \(activeAgents)"
        if let auth, auth.reloginRequired {
            return base + " · 로그인 갱신 필요"
        }
        return base
    }

    enum CodingKeys: String, CodingKey {
        case profile
        case display
        case status
        case activeAgents = "active_agents"
        case safeActions = "safe_actions"
        case lastSignal = "last_signal"
        case auth
    }
}

struct ProfileAuthHealth: Codable {
    let provider: String
    let status: String
    let authFilePresent: Bool
    let providerPresent: Bool
    let tokensPresent: Bool
    let accessTokenPresent: Bool
    let refreshTokenPresent: Bool
    let lastAuthErrorCode: String?
    let reloginRequired: Bool
    let metadataOnly: Bool

    enum CodingKeys: String, CodingKey {
        case provider
        case status
        case authFilePresent = "auth_file_present"
        case providerPresent = "provider_present"
        case tokensPresent = "tokens_present"
        case accessTokenPresent = "access_token_present"
        case refreshTokenPresent = "refresh_token_present"
        case lastAuthErrorCode = "last_auth_error_code"
        case reloginRequired = "relogin_required"
        case metadataOnly = "metadata_only"
    }

    var menuLine: String {
        if reloginRequired {
            return "Codex Model Auth · 재로그인 필요" + (lastAuthErrorCode.map { " · \($0)" } ?? "")
        }
        if status == "stale_error" {
            return "Codex Model Auth · 토큰 있음 · 이전 오류 기록"
        }
        if tokensPresent {
            return "Codex Model Auth · 정상 · token 있음"
        }
        if authFilePresent {
            return "Codex Model Auth · \(status) · token 없음"
        }
        return "Codex Model Auth · 설정 없음"
    }
}

struct FleetActionResult: Codable {
    let ok: Bool
    let dryRun: Bool?
    let message: String?
    let plan: FleetActionPlan?

    enum CodingKeys: String, CodingKey {
        case ok
        case dryRun = "dry_run"
        case message
        case plan
    }

    var displaySummary: String {
        if let plan {
            if plan.targets.isEmpty {
                return "Dry-run 확인 · " + (message ?? "No matching profiles; no gateway action planned.")
            }
            let scope = plan.degradedOnly == true ? "degraded-only" : "group"
            return "Dry-run \(scope) \(plan.action) · " + plan.targets.joined(separator: ", ")
        }
        return message ?? (ok ? "Action planned." : "Action failed.")
    }
}

struct FleetActionPlan: Codable {
    let action: String
    let group: String?
    let targets: [String]
    let safe: Bool
    let force: Bool
    let dryRun: Bool
    let command: [String]
    let degradedOnly: Bool?

    enum CodingKeys: String, CodingKey {
        case action
        case group
        case targets
        case safe
        case force
        case dryRun = "dry_run"
        case command
        case degradedOnly = "degraded_only"
    }
}

struct LaunchAgentResult: Codable {
    let ok: Bool
    let launchagent: LaunchAgentState?
    let message: String?
}

struct LaunchAgentState: Codable {
    let label: String
    let plist: String
    let installed: Bool
    let enabled: Bool
    let loaded: Bool

    var menuLine: String {
        if !installed { return "자동실행 · not installed" }
        return enabled ? "자동실행 · enabled" : "자동실행 · disabled"
    }
}

struct WatchdogResult: Codable {
    let ok: Bool
    let watchdog: WatchdogSummary?
    let message: String?
}

struct WatchdogSummary: Codable {
    let policy: String
    let groups: [String]
    let actions: [FleetActionResult]
    let message: String

    var displaySummary: String {
        if actions.isEmpty { return "Watchdog \(policy) · \(message)" }
        return "Watchdog \(policy) · \(actions.count) action(s) evaluated"
    }
}

struct AuthRepairResult: Codable {
    let ok: Bool
    let profile: String?
    let provider: String?
    let action: String?
    let openedTerminal: Bool?
    let message: String?

    enum CodingKeys: String, CodingKey {
        case ok
        case profile
        case provider
        case action
        case openedTerminal = "opened_terminal"
        case message
    }

    var displaySummary: String {
        let opened = openedTerminal == true ? "opened Terminal" : "prepared"
        return "Auth Repair · \(opened) · \(profile ?? "profile") · \(action ?? "action")"
    }
}

struct ProfileMapResult: Codable {
    let ok: Bool
    let profile: String?
    let mapFile: String?
    let message: String?

    enum CodingKeys: String, CodingKey {
        case ok
        case profile
        case mapFile = "map_file"
        case message
    }

    var displaySummary: String {
        if ok {
            return "프로필 분류 저장 · \(profile ?? "profile")"
        }
        return message ?? "프로필 분류 저장 실패"
    }
}
