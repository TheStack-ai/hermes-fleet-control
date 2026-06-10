import AppKit
import SwiftUI

@main
struct HermesFleetControlApp: App {
    @StateObject private var viewModel = FleetViewModel()

    var body: some Scene {
        MenuBarExtra("Hermes Fleet", systemImage: menuIcon) {
            FleetMenuView(viewModel: viewModel)
        }
        .menuBarExtraStyle(.window)
    }

    private var menuIcon: String {
        guard let snapshot = viewModel.snapshot else { return "bolt.circle" }
        let hasStopped = snapshot.servers.contains { $0.summary.stopped > 0 }
        let hasDegraded = snapshot.servers.contains { $0.summary.degraded > 0 || $0.summary.unknown > 0 }
        let hasBusy = snapshot.servers.contains { $0.summary.busy > 0 }
        if hasStopped { return "xmark.octagon.fill" }
        if hasDegraded { return "exclamationmark.triangle.fill" }
        if hasBusy { return "clock.badge.fill" }
        return "bolt.circle.fill"
    }
}
