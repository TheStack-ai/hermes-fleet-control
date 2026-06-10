import Foundation

struct FleetCLI {
    let repoRoot: URL
    let pythonPath: String

    init(
        repoRoot: URL = FleetCLI.defaultRepoRoot(),
        pythonPath: String = FleetCLI.defaultPythonPath()
    ) {
        self.repoRoot = repoRoot
        self.pythonPath = pythonPath
    }

    private static func defaultRepoRoot() -> URL {
        let env = ProcessInfo.processInfo.environment
        if let configured = env["HERMES_FLEET_ROOT"], !configured.isEmpty {
            return URL(fileURLWithPath: configured)
        }
        let bundleURL = Bundle.main.bundleURL
        if bundleURL.pathExtension == "app" {
            // Packaged as <repo>/dist/HermesFleetControl.app during local builds.
            return bundleURL.deletingLastPathComponent().deletingLastPathComponent()
        }
        return URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
    }

    private static func defaultPythonPath() -> String {
        let env = ProcessInfo.processInfo.environment
        if let configured = env["HERMES_FLEET_PYTHON"], !configured.isEmpty {
            return configured
        }
        return "/usr/bin/python3"
    }

    func status(skipNetwork: Bool = false) throws -> FleetSnapshot {
        var args = [repoRoot.appendingPathComponent("control/fleetctl.py").path, "status", "--json"]
        if skipNetwork {
            args.append("--skip-network")
        }
        let data = try run(args: args)
        return try JSONDecoder().decode(FleetSnapshot.self, from: data)
    }

    func dryRunReconnect(group: String, degradedOnly: Bool = false) throws -> FleetActionResult {
        return try reconnect(group: group, degradedOnly: degradedOnly, dryRun: true)
    }

    func liveReconnectDegraded(group: String) throws -> FleetActionResult {
        return try reconnect(group: group, degradedOnly: true, dryRun: false)
    }

    func launchAgent(action: String) throws -> LaunchAgentResult {
        let args = [
            repoRoot.appendingPathComponent("control/fleetctl.py").path,
            "launchagent",
            action,
            "--json"
        ]
        let data = try run(args: args)
        return try JSONDecoder().decode(LaunchAgentResult.self, from: data)
    }

    func watchdog(policy: String) throws -> WatchdogResult {
        let args = [
            repoRoot.appendingPathComponent("control/fleetctl.py").path,
            "watchdog",
            "--policy", policy,
            "--json",
            "--skip-network"
        ]
        let data = try run(args: args)
        return try JSONDecoder().decode(WatchdogResult.self, from: data)
    }

    func authRepair(profile: String, action: String) throws -> AuthRepairResult {
        let args = [
            repoRoot.appendingPathComponent("control/fleetctl.py").path,
            "auth-repair",
            "--profile", profile,
            "--action", action,
            "--open-terminal",
            "--json"
        ]
        let data = try run(args: args)
        return try JSONDecoder().decode(AuthRepairResult.self, from: data)
    }

    private func reconnect(group: String, degradedOnly: Bool, dryRun: Bool) throws -> FleetActionResult {
        var args = [
            repoRoot.appendingPathComponent("control/fleetctl.py").path,
            "reconnect",
            "--group", group,
            "--safe",
            "--json",
            "--skip-network"
        ]
        if dryRun {
            args.append("--dry-run")
        }
        if degradedOnly {
            args.append("--degraded-only")
        }
        let data = try run(args: args)
        return try JSONDecoder().decode(FleetActionResult.self, from: data)
    }

    private func run(args: [String]) throws -> Data {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: pythonPath)
        process.arguments = args
        process.currentDirectoryURL = repoRoot

        var environment = ProcessInfo.processInfo.environment
        environment["HERMES_FLEET_ROOT"] = repoRoot.path
        process.environment = environment

        let stdout = Pipe()
        let stderr = Pipe()
        process.standardOutput = stdout
        process.standardError = stderr
        try process.run()
        process.waitUntilExit()

        let data = stdout.fileHandleForReading.readDataToEndOfFile()
        if process.terminationStatus != 0 {
            let errorData = stderr.fileHandleForReading.readDataToEndOfFile()
            let message = String(data: errorData, encoding: .utf8) ?? "fleetctl failed"
            throw NSError(domain: "FleetCLI", code: Int(process.terminationStatus), userInfo: [NSLocalizedDescriptionKey: message])
        }
        return data
    }
}
