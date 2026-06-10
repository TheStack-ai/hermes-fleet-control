import Foundation
import UserNotifications

@MainActor
final class FleetNotificationManager {
    static let shared = FleetNotificationManager()

    private let center = UNUserNotificationCenter.current()
    private init() {}

    func requestAuthorization() async -> Bool {
        do {
            return try await center.requestAuthorization(options: [.alert, .sound])
        } catch {
            return false
        }
    }

    func sendAttentionAlert(title: String, body: String) {
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default
        let request = UNNotificationRequest(identifier: "fleet-attention-\(UUID().uuidString)", content: content, trigger: nil)
        center.add(request)
    }
}
