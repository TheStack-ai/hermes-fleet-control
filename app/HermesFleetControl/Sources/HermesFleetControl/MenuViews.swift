import AppKit
import SwiftUI

@MainActor
final class FleetViewModel: ObservableObject {
    @Published var snapshot: FleetSnapshot?
    @Published var lastError: String?
    @Published var lastActionSummary: String?
    @Published var isRefreshing = false
    @Published var isPlanningAction = false
    @Published var armedLiveReconnectGroup: String?
    @Published var alertsEnabled: Bool
    @Published var launchAgentState: LaunchAgentState?

    private let cli = FleetCLI()
    private let notifier = FleetNotificationManager.shared
    private var pollTimer: Timer?
    private let alertsKey = "fleetAlertsEnabled"

    init() {
        self.alertsEnabled = UserDefaults.standard.bool(forKey: alertsKey)
        startPolling()
    }

    func startPolling() {
        guard pollTimer == nil else { return }
        pollTimer = Timer.scheduledTimer(withTimeInterval: 60, repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.refresh()
            }
        }
    }

    func setAlertsEnabled(_ enabled: Bool) {
        if !enabled {
            alertsEnabled = false
            UserDefaults.standard.set(false, forKey: alertsKey)
            return
        }
        Task {
            let granted = await notifier.requestAuthorization()
            alertsEnabled = granted
            UserDefaults.standard.set(granted, forKey: alertsKey)
            if !granted {
                lastError = "Notification permission was not granted."
            }
        }
    }

    func refreshLaunchAgentStatus() {
        Task.detached { [cli] in
            do {
                let result = try cli.launchAgent(action: "status")
                await MainActor.run {
                    self.launchAgentState = result.launchagent
                }
            } catch {
                await MainActor.run { self.lastError = error.localizedDescription }
            }
        }
    }

    func runLaunchAgent(action: String) {
        isPlanningAction = true
        lastError = nil
        Task.detached { [cli] in
            do {
                let result = try cli.launchAgent(action: action)
                await MainActor.run {
                    self.launchAgentState = result.launchagent
                    self.lastActionSummary = result.launchagent?.menuLine ?? (result.ok ? "자동실행 \(action) 완료" : "자동실행 \(action) 실패")
                    self.isPlanningAction = false
                }
            } catch {
                await MainActor.run {
                    self.lastError = error.localizedDescription
                    self.isPlanningAction = false
                }
            }
        }
    }

    func runWatchdog(policy: String) {
        isPlanningAction = true
        lastError = nil
        Task.detached { [cli] in
            do {
                let result = try cli.watchdog(policy: policy)
                await MainActor.run {
                    self.lastActionSummary = result.watchdog?.displaySummary ?? (result.ok ? "Watchdog 점검 완료" : "Watchdog 점검 실패")
                    self.isPlanningAction = false
                    self.refresh()
                }
            } catch {
                await MainActor.run {
                    self.lastError = error.localizedDescription
                    self.isPlanningAction = false
                }
            }
        }
    }

    func openAuthRepair(profile: String, action: String) {
        isPlanningAction = true
        lastError = nil
        Task.detached { [cli] in
            do {
                let result = try cli.authRepair(profile: profile, action: action)
                await MainActor.run {
                    self.lastActionSummary = result.displaySummary
                    self.isPlanningAction = false
                    self.refresh()
                }
            } catch {
                await MainActor.run {
                    self.lastError = error.localizedDescription
                    self.isPlanningAction = false
                }
            }
        }
    }

    func refresh() {
        isRefreshing = true
        lastError = nil
        Task.detached { [cli] in
            do {
                let snapshot = try cli.status(skipNetwork: true)
                await MainActor.run {
                    let previous = self.snapshot
                    self.snapshot = snapshot
                    self.maybeNotifyAttentionTransition(previous: previous, current: snapshot)
                    self.isRefreshing = false
                }
            } catch {
                await MainActor.run {
                    self.lastError = error.localizedDescription
                    self.isRefreshing = false
                }
            }
        }
    }

    func dryRunReconnect(group: String, degradedOnly: Bool) {
        isPlanningAction = true
        lastError = nil
        Task.detached { [cli] in
            do {
                let result = try cli.dryRunReconnect(group: group, degradedOnly: degradedOnly)
                await MainActor.run {
                    self.lastActionSummary = result.displaySummary
                    self.armedLiveReconnectGroup = nil
                    self.isPlanningAction = false
                }
            } catch {
                await MainActor.run {
                    self.lastError = error.localizedDescription
                    self.armedLiveReconnectGroup = nil
                    self.isPlanningAction = false
                }
            }
        }
    }

    func previewLiveReconnectDegraded(group: String) {
        isPlanningAction = true
        lastError = nil
        Task.detached { [cli] in
            do {
                let result = try cli.dryRunReconnect(group: group, degradedOnly: true)
                await MainActor.run {
                    self.lastActionSummary = "Live 실행 전 확인 · " + result.displaySummary
                    self.armedLiveReconnectGroup = result.plan?.targets.isEmpty == false ? group : nil
                    self.isPlanningAction = false
                }
            } catch {
                await MainActor.run {
                    self.lastError = error.localizedDescription
                    self.armedLiveReconnectGroup = nil
                    self.isPlanningAction = false
                }
            }
        }
    }

    func confirmLiveReconnectDegraded(group: String) {
        guard armedLiveReconnectGroup == group else { return }
        isPlanningAction = true
        lastError = nil
        Task.detached { [cli] in
            do {
                let result = try cli.liveReconnectDegraded(group: group)
                await MainActor.run {
                    self.lastActionSummary = "Live 실행 완료 · " + result.displaySummary
                    self.armedLiveReconnectGroup = nil
                    self.isPlanningAction = false
                    self.refresh()
                }
            } catch {
                await MainActor.run {
                    self.lastError = error.localizedDescription
                    self.armedLiveReconnectGroup = nil
                    self.isPlanningAction = false
                }
            }
        }
    }

    private func maybeNotifyAttentionTransition(previous: FleetSnapshot?, current: FleetSnapshot) {
        guard alertsEnabled, let previous else { return }
        let newAttention = current.attentionProfileKeys.subtracting(previous.attentionProfileKeys)
        if !newAttention.isEmpty {
            let names = current.attentionProfiles
                .filter { newAttention.contains($0.profile) }
                .map { $0.display ?? $0.profile }
                .joined(separator: ", ")
            notifier.sendAttentionAlert(
                title: "Hermes Fleet · 확인 필요",
                body: "새로 문제 감지: \(names)"
            )
            return
        }
        if !previous.attentionProfileKeys.isEmpty && current.attentionProfileKeys.isEmpty {
            notifier.sendAttentionAlert(
                title: "Hermes Fleet · 정상 복구",
                body: "All configured profiles are ready."
            )
        }
    }
}

struct FleetMenuView: View {
    @ObservedObject var viewModel: FleetViewModel

    private let sponsorURL = URL(string: "https://github.com/sponsors/TheStack-ai")!
    private let repoURL = URL(string: "https://github.com/TheStack-ai")!

    var body: some View {
        VStack(spacing: 0) {
            headerCard
            Divider().padding(.horizontal, 16)
            ScrollView(.vertical, showsIndicators: true) {
                VStack(alignment: .leading, spacing: 12) {
                    attentionSection
                    fleetSection
                    operationsSection
                    supportSection
                }
                .padding(16)
                .frame(maxWidth: .infinity, alignment: .topLeading)
            }
            // MenuBarExtra(.window) does not reliably infer a useful ideal height
            // for nested ScrollView content. Without an explicit body height the
            // popover can collapse to just header + footer on macOS, hiding the
            // premium profile/control/support cards.
            .frame(height: 520)
            Divider().padding(.horizontal, 16)
            footerBar
        }
        .frame(width: 452)
        .background(.regularMaterial)
        .onAppear {
            viewModel.refresh()
            viewModel.refreshLaunchAgentStatus()
        }
    }

    @ViewBuilder
    private var headerCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 12) {
                ZStack {
                    RoundedRectangle(cornerRadius: 14, style: .continuous)
                        .fill(.thinMaterial)
                        .overlay(
                            RoundedRectangle(cornerRadius: 14, style: .continuous)
                                .stroke(.primary.opacity(0.10), lineWidth: 1)
                        )
                    Image(systemName: headerSymbol)
                        .font(.system(size: 24, weight: .semibold))
                        .symbolRenderingMode(.hierarchical)
                        .foregroundStyle(headerTint)
                }
                .frame(width: 48, height: 48)

                VStack(alignment: .leading, spacing: 3) {
                    Text("Hermes Fleet Control")
                        .font(.system(size: 16, weight: .semibold, design: .rounded))
                    Text(headerSubtitle)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Button {
                    viewModel.refresh()
                } label: {
                    Image(systemName: "arrow.clockwise")
                        .font(.system(size: 14, weight: .semibold))
                        .frame(width: 30, height: 30)
                }
                .buttonStyle(.borderless)
                .help("상태 새로고침 · Refresh Now")
            }

            if let snapshot = viewModel.snapshot {
                HStack(spacing: 8) {
                    MetricPill(title: "Ready", value: "\(snapshot.readyCount)", systemImage: "checkmark.seal.fill", tint: .green)
                    MetricPill(title: "Gateway", value: "\(snapshot.attentionCount)", systemImage: "wrench.and.screwdriver.fill", tint: snapshot.attentionCount > 0 ? .orange : .green)
                    MetricPill(title: "Auth", value: "\(snapshot.reloginCount)", systemImage: "key.fill", tint: snapshot.reloginCount > 0 ? .orange : .green)
                }
            }
        }
        .padding(16)
    }

    @ViewBuilder
    private var attentionSection: some View {
        if let snapshot = viewModel.snapshot, snapshot.hasAttention {
            PremiumCard {
                VStack(alignment: .leading, spacing: 10) {
                    Label("조치가 필요한 프로필", systemImage: "key.viewfinder")
                        .font(.system(size: 13, weight: .semibold))
                    Text("Gateway 상태와 모델 인증 상태를 분리해서 보여줘. Discord가 온라인이어도 Codex OAuth가 만료되면 여기서 바로 복구할 수 있어.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    ForEach(snapshot.priorityProfiles) { profile in
                        HStack(spacing: 10) {
                            Image(systemName: profile.auth?.reloginRequired == true ? "key.fill" : profile.status.symbolName)
                                .symbolRenderingMode(.hierarchical)
                                .foregroundStyle(profileTint(profile))
                                .frame(width: 22)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(profile.display ?? profile.profile)
                                    .font(.system(size: 13, weight: .medium))
                                Text(priorityReason(profile))
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                            if profile.auth?.reloginRequired == true {
                                Button("Re-auth") {
                                    viewModel.openAuthRepair(profile: profile.profile, action: "reauth")
                                }
                                .controlSize(.small)
                                .buttonStyle(.borderedProminent)
                                .tint(.orange)
                                .disabled(viewModel.isPlanningAction)
                            }
                        }
                    }
                }
            }
        }
    }

    @ViewBuilder
    private var fleetSection: some View {
        if let snapshot = viewModel.snapshot {
            VStack(alignment: .leading, spacing: 8) {
                SectionTitle("Profiles", subtitle: "Live status · visible by default")
                ForEach(snapshot.servers) { server in
                    PremiumCard {
                        VStack(alignment: .leading, spacing: 10) {
                            HStack(spacing: 10) {
                                Image(systemName: server.summary.symbolName)
                                    .symbolRenderingMode(.hierarchical)
                                    .foregroundStyle(serverTint(server))
                                    .frame(width: 24)
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(server.menuTitle)
                                        .font(.system(size: 13, weight: .semibold))
                                    Text(server.summary.premiumLine)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                                Spacer()
                                Text(server.summary.isHealthy ? "READY" : "CHECK")
                                    .font(.caption2.weight(.bold))
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 4)
                                    .background(serverTint(server).opacity(0.14), in: Capsule())
                                    .foregroundStyle(serverTint(server))
                            }
                            LazyVGrid(columns: [GridItem(.flexible(), spacing: 8), GridItem(.flexible(), spacing: 8)], spacing: 8) {
                                ForEach(server.profiles) { profile in
                                    compactProfileTile(profile)
                                }
                            }
                            DisclosureGroup {
                                VStack(alignment: .leading, spacing: 8) {
                                    Text(server.summary.compactLine)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                    ForEach(server.profiles) { profile in
                                        profileRow(profile)
                                    }
                                    Divider().padding(.vertical, 2)
                                    groupedReconnectControls(server)
                                }
                                .padding(.top, 8)
                            } label: {
                                Label("상세 로그와 작업 버튼", systemImage: "slider.horizontal.3")
                                    .font(.system(size: 12, weight: .medium))
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                    .disabled(viewModel.isPlanningAction)
                }
            }
        } else if let error = viewModel.lastError {
            PremiumCard {
                Label("Fleet 상태 조회 실패", systemImage: "xmark.octagon.fill")
                    .font(.system(size: 13, weight: .semibold))
                Text(error).font(.caption).foregroundStyle(.secondary)
            }
        }
    }

    private func profileRow(_ profile: FleetProfile) -> some View {
        DisclosureGroup {
            VStack(alignment: .leading, spacing: 8) {
                Text(profile.auth?.menuLine ?? "Codex Login · unknown")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Text(profile.lastSignal)
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
                HStack(spacing: 8) {
                    ActionChip("로그인 다시하기", "Re-auth", "key.fill") {
                        viewModel.openAuthRepair(profile: profile.profile, action: "reauth")
                    }
                    ActionChip("테스트", "Smoke", "checkmark.seal") {
                        viewModel.openAuthRepair(profile: profile.profile, action: "smoke")
                    }
                    ActionChip("재시작", "Restart", "arrow.triangle.2.circlepath.circle") {
                        viewModel.openAuthRepair(profile: profile.profile, action: "restart")
                    }
                }
                Button {
                    viewModel.openAuthRepair(profile: profile.profile, action: "reauth-manual")
                } label: {
                    Label("수동 코드 로그인 · Manual Paste", systemImage: "doc.on.clipboard")
                }
                .buttonStyle(.plain)
                .font(.caption)
            }
            .padding(.top, 8)
        } label: {
            HStack(spacing: 10) {
                Image(systemName: profile.auth?.reloginRequired == true ? "key.fill" : profile.status.symbolName)
                    .symbolRenderingMode(.hierarchical)
                    .foregroundStyle(profileTint(profile))
                    .frame(width: 20)
                VStack(alignment: .leading, spacing: 2) {
                    Text(profile.display ?? profile.profile)
                        .font(.system(size: 13, weight: .medium))
                    Text(profile.status.shortLabel + " · active \(profile.activeAgents)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                if profile.auth?.reloginRequired == true {
                    Text("Auth Fix")
                        .font(.caption2.weight(.semibold))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(.primary.opacity(0.08), in: Capsule())
                }
            }
        }
        .padding(10)
        .background(.primary.opacity(0.035), in: RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private func compactProfileTile(_ profile: FleetProfile) -> some View {
        HStack(spacing: 8) {
            Circle()
                .fill(profileTint(profile))
                .frame(width: 8, height: 8)
            VStack(alignment: .leading, spacing: 1) {
                Text(profile.display ?? profile.profile)
                    .font(.system(size: 12, weight: .semibold))
                    .lineLimit(1)
                Text(profile.auth?.reloginRequired == true ? "Auth fix" : profile.status.shortLabel)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            Spacer(minLength: 0)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(profileTint(profile).opacity(0.08), in: RoundedRectangle(cornerRadius: 12, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: 12, style: .continuous).stroke(profileTint(profile).opacity(0.18), lineWidth: 1))
        .accessibilityLabel("\(profile.display ?? profile.profile), \(profile.status.shortLabel)")
    }

    private func groupedReconnectControls(_ server: FleetServer) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                ActionChip("문제만 확인", "Preview", "wave.3.right.circle") {
                    viewModel.dryRunReconnect(group: server.key, degradedOnly: true)
                }
                ActionChip("전체 확인", "Group", "rectangle.stack.badge.play") {
                    viewModel.dryRunReconnect(group: server.key, degradedOnly: false)
                }
            }
            HStack(spacing: 8) {
                ActionChip("Live 전 확인", "Arm", "exclamationmark.shield") {
                    viewModel.previewLiveReconnectDegraded(group: server.key)
                }
                if viewModel.armedLiveReconnectGroup == server.key {
                    ActionChip("확인 후 실행", "Confirm", "checkmark.shield.fill") {
                        viewModel.confirmLiveReconnectDegraded(group: server.key)
                    }
                }
            }
        }
    }

    private var operationsSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            SectionTitle("Control", subtitle: "Preview first · local only")
            PremiumCard {
                VStack(alignment: .leading, spacing: 10) {
                    HStack(spacing: 8) {
                        ActionTile(title: viewModel.alertsEnabled ? "알림 끄기" : "알림 켜기", subtitle: viewModel.alertsEnabled ? "Alerts Off" : "Alerts On", systemImage: viewModel.alertsEnabled ? "bell.slash" : "bell.badge") {
                            viewModel.setAlertsEnabled(!viewModel.alertsEnabled)
                        }
                        ActionTile(title: "안전점검", subtitle: "Watchdog Preview", systemImage: "shield.lefthalf.filled") {
                            viewModel.runWatchdog(policy: "dry-run")
                        }
                    }
                    HStack(spacing: 8) {
                        ActionTile(title: "자동복구", subtitle: "Run Recovery", systemImage: "shield.checkered") {
                            viewModel.runWatchdog(policy: "auto")
                        }
                        ActionTile(title: "새로고침", subtitle: "Refresh Now", systemImage: "arrow.clockwise.circle") {
                            viewModel.refresh()
                        }
                    }
                    DisclosureGroup {
                        VStack(alignment: .leading, spacing: 8) {
                            if let state = viewModel.launchAgentState {
                                Text(state.menuLine).font(.caption).foregroundStyle(.secondary)
                            }
                            Button("상태 새로고침 · Refresh") { viewModel.refreshLaunchAgentStatus() }
                            Button("자동실행 설치/복구 · Install") { viewModel.runLaunchAgent(action: "install") }
                            Button("자동실행 켜기 · Enable") { viewModel.runLaunchAgent(action: "enable") }
                            Button("자동실행 끄기 · Disable") { viewModel.runLaunchAgent(action: "disable") }
                            Button("자동실행 제거 · Uninstall") { viewModel.runLaunchAgent(action: "uninstall") }
                        }
                        .font(.caption)
                        .padding(.top, 6)
                    } label: {
                        Label("자동실행 · Autostart", systemImage: "power.circle")
                            .font(.system(size: 13, weight: .medium))
                    }
                }
            }
        }
    }

    private var supportSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            SectionTitle("About", subtitle: "Project links")
            PremiumCard {
                VStack(alignment: .leading, spacing: 10) {
                    HStack(spacing: 10) {
                        Image(systemName: "heart.circle.fill")
                            .font(.system(size: 24, weight: .semibold))
                            .symbolRenderingMode(.hierarchical)
                        VStack(alignment: .leading, spacing: 2) {
                            Text("후원하기 · Sponsor")
                                .font(.system(size: 13, weight: .semibold))
                            Text("GitHub Sponsors와 프로젝트 프로필")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                    HStack(spacing: 8) {
                        ActionChip("Sponsor", "GitHub", "heart.fill") { openURL(sponsorURL) }
                        ActionChip("Profile", "GitHub", "person.crop.circle") { openURL(repoURL) }
                    }
                }
            }
        }
    }

    @ViewBuilder
    private var footerBar: some View {
        HStack(spacing: 10) {
            if viewModel.isPlanningAction {
                ProgressView().controlSize(.small)
                Label("실행 준비 중", systemImage: "hourglass")
                    .foregroundStyle(.secondary)
            } else if viewModel.isRefreshing {
                ProgressView().controlSize(.small)
                Label("상태 새로고침 중", systemImage: "arrow.clockwise")
                    .foregroundStyle(.secondary)
            } else if let error = viewModel.lastError, viewModel.snapshot != nil {
                Label("오류", systemImage: "exclamationmark.triangle")
                    .foregroundStyle(.secondary)
                Text(error).lineLimit(1).foregroundStyle(.tertiary)
            } else if let action = viewModel.lastActionSummary {
                Label(action, systemImage: "checkmark.circle")
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            } else {
                Label("Local only · secrets never shown", systemImage: "lock.shield")
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Button("Quit") { NSApplication.shared.terminate(nil) }
                .keyboardShortcut("q")
        }
        .font(.caption)
        .padding(14)
    }

    private var headerSymbol: String {
        guard let snapshot = viewModel.snapshot else { return "bolt.circle" }
        if snapshot.servers.contains(where: { $0.summary.stopped > 0 }) { return "xmark.octagon.fill" }
        if snapshot.hasAttention { return "exclamationmark.triangle.fill" }
        return "bolt.circle.fill"
    }

    private var headerTint: Color {
        guard let snapshot = viewModel.snapshot else { return .blue }
        if snapshot.servers.contains(where: { $0.summary.stopped > 0 }) { return .red }
        if snapshot.hasAttention { return .orange }
        return .green
    }

    private func serverTint(_ server: FleetServer) -> Color {
        if server.summary.stopped > 0 { return .red }
        if server.summary.degraded > 0 || server.summary.unknown > 0 { return .orange }
        if server.summary.busy > 0 { return .blue }
        return .green
    }

    private func profileTint(_ profile: FleetProfile) -> Color {
        if profile.auth?.reloginRequired == true { return .orange }
        switch profile.status {
        case .healthy: return .green
        case .degradedBackoff, .unknown: return .orange
        case .busy: return .blue
        case .stopped: return .red
        }
    }

    private var headerSubtitle: String {
        guard let snapshot = viewModel.snapshot else {
            return viewModel.isRefreshing ? "새로고침 중 · Refreshing" : "로컬 상태 준비 중 · Waiting for snapshot"
        }
        return snapshot.headline + " · " + snapshot.generatedAt
    }

    private var cardBackground: some ShapeStyle {
        .primary.opacity(0.045)
    }

    private func priorityReason(_ profile: FleetProfile) -> String {
        if profile.auth?.reloginRequired == true { return "Codex Model Auth 만료 · Discord 연결은 별도" }
        switch profile.status {
        case .stopped: return "Gateway 꺼짐 · Offline"
        case .degradedBackoff: return "재연결 대기 · Backoff"
        case .unknown: return "상태 확인 필요 · Unknown"
        case .busy: return "작업중 · Busy"
        case .healthy: return "정상 · Ready"
        }
    }

    private func openURL(_ url: URL) {
        NSWorkspace.shared.open(url)
    }
}

private struct SectionTitle: View {
    let title: String
    let subtitle: String

    init(_ title: String, subtitle: String) {
        self.title = title
        self.subtitle = subtitle
    }

    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            Text(title)
                .font(.system(size: 12, weight: .semibold, design: .rounded))
                .textCase(.uppercase)
                .foregroundStyle(.primary)
            Text(subtitle)
                .font(.caption2)
                .foregroundStyle(.tertiary)
            Spacer()
        }
        .padding(.horizontal, 2)
    }
}

private struct PremiumCard<Content: View>: View {
    @ViewBuilder var content: Content

    var body: some View {
        content
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .fill(.primary.opacity(0.045))
                    .overlay(
                        RoundedRectangle(cornerRadius: 16, style: .continuous)
                            .stroke(.primary.opacity(0.08), lineWidth: 1)
                    )
            )
    }
}

private struct MetricPill: View {
    let title: String
    let value: String
    let systemImage: String
    let tint: Color

    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: systemImage)
                .symbolRenderingMode(.hierarchical)
                .foregroundStyle(tint)
            Text(value)
                .font(.system(size: 12, weight: .semibold, design: .rounded))
            Text(title)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(tint.opacity(0.10), in: Capsule())
        .overlay(Capsule().stroke(tint.opacity(0.18), lineWidth: 1))
        .accessibilityLabel("\(title) \(value)")
    }
}

private struct ActionTile: View {
    let title: String
    let subtitle: String
    let systemImage: String
    let action: () -> Void

    init(title: String, subtitle: String, systemImage: String, action: @escaping () -> Void) {
        self.title = title
        self.subtitle = subtitle
        self.systemImage = systemImage
        self.action = action
    }

    var body: some View {
        Button(action: action) {
            VStack(alignment: .leading, spacing: 8) {
                Image(systemName: systemImage)
                    .font(.system(size: 18, weight: .semibold))
                    .symbolRenderingMode(.hierarchical)
                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.system(size: 12, weight: .semibold))
                    Text(subtitle)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(12)
            .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).stroke(.primary.opacity(0.08), lineWidth: 1))
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(title), \(subtitle)")
    }
}

private struct ActionChip: View {
    let title: String
    let subtitle: String
    let systemImage: String
    let action: () -> Void

    init(_ title: String, _ subtitle: String, _ systemImage: String, action: @escaping () -> Void) {
        self.title = title
        self.subtitle = subtitle
        self.systemImage = systemImage
        self.action = action
    }

    var body: some View {
        Button(action: action) {
            Label {
                VStack(alignment: .leading, spacing: 0) {
                    Text(title)
                        .font(.caption.weight(.semibold))
                    Text(subtitle)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            } icon: {
                Image(systemName: systemImage)
                    .symbolRenderingMode(.hierarchical)
            }
            .padding(.horizontal, 9)
            .padding(.vertical, 7)
            .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 10, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 10, style: .continuous).stroke(.primary.opacity(0.08), lineWidth: 1))
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(title), \(subtitle)")
    }
}
