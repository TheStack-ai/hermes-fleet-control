import AppKit
import SwiftUI

@main
struct HermesFleetControlApp: App {
    @StateObject private var viewModel = FleetViewModel()

    var body: some Scene {
        MenuBarExtra {
            FleetMenuView(viewModel: viewModel)
        } label: {
            Image(nsImage: FleetMenuBarIcon.image)
                .accessibilityLabel("Hermes Fleet Control")
        }
        .menuBarExtraStyle(.window)
    }
}

private enum FleetMenuBarIcon {
    static let image: NSImage = {
        let size = NSSize(width: 18, height: 18)
        let image = NSImage(size: size)
        image.lockFocus()
        defer { image.unlockFocus() }

        NSColor.black.setFill()
        let railWidth: CGFloat = 4.2
        let radius: CGFloat = 2.1
        let leftX: CGFloat = 3.8
        let rightX: CGFloat = 10.0
        let topY: CGFloat = 2.5
        let height: CGFloat = 13.0
        let bridgeY: CGFloat = 7.0
        let bridgeHeight: CGFloat = 4.0

        NSBezierPath(
            roundedRect: NSRect(x: leftX, y: topY, width: railWidth, height: height),
            xRadius: radius,
            yRadius: radius
        ).fill()
        NSBezierPath(
            roundedRect: NSRect(x: rightX, y: topY, width: railWidth, height: height),
            xRadius: radius,
            yRadius: radius
        ).fill()
        NSBezierPath(
            roundedRect: NSRect(x: leftX, y: bridgeY, width: rightX + railWidth - leftX, height: bridgeHeight),
            xRadius: radius,
            yRadius: radius
        ).fill()

        image.isTemplate = true
        return image
    }()
}
