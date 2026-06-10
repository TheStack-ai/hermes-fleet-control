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
            if let resources = Bundle.main.resourceURL {
                let bundledCLI = resources.appendingPathComponent("control/fleetctl.py")
                if FileManager.default.fileExists(atPath: bundledCLI.path) {
                    return resources
                }
            }
            // Development fallback: packaged as <repo>/dist/HermesFleetControl.app.
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

    func mapProfile(profile: String, display: String, server: String? = nil, serverDisplay: String? = nil, state: String = "managed") throws -> ProfileMapResult {
        var args = [
            repoRoot.appendingPathComponent("control/fleetctl.py").path,
            "profile-map",
            "--profile", profile,
            "--display", display,
            "--state", state,
            "--json"
        ]
        if let server, !server.isEmpty {
            args.append(contentsOf: ["--server", server])
        }
        if let serverDisplay, !serverDisplay.isEmpty {
            args.append(contentsOf: ["--server-display", serverDisplay])
        }
        let data = try run(args: args)
        return try JSONDecoder().decode(ProfileMapResult.self, from: data)
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
        environment["HERMES_FLEET_APP_PATH"] = Bundle.main.bundleURL.path
        if environment["HERMES_FLEET_RUNTIME_DIR"] == nil {
            let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            if let runtimeRoot = appSupport?.appendingPathComponent("HermesFleetControl", isDirectory: true).appendingPathComponent("runtime", isDirectory: true) {
                environment["HERMES_FLEET_RUNTIME_DIR"] = runtimeRoot.path
                environment["HERMES_FLEET_AUTH_REPAIR_DIR"] = runtimeRoot.appendingPathComponent("auth-repair", isDirectory: true).path
                environment["HERMES_FLEET_AUDIT_LOG"] = runtimeRoot.appendingPathComponent("audit/actions.jsonl").path
            }
        }
        process.environment = environment

        let stdout = Pipe()
        let stderr = Pipe()
        process.standardOutput = stdout
        process.standardError = stderr
        try process.run()
        process.waitUntilExit()

        let data = stdout.fileHandleForReading.readDataToEndOfFile()
        let errorData = stderr.fileHandleForReading.readDataToEndOfFile()
        if process.terminationStatus != 0 {
            let stderrText = String(data: errorData, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            let stdoutText = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            let message = FleetCLI.errorMessage(stderrText: stderrText, stdoutText: stdoutText)
            throw NSError(domain: "FleetCLI", code: Int(process.terminationStatus), userInfo: [NSLocalizedDescriptionKey: message])
        }
        return data
    }

    private static func errorMessage(stderrText: String, stdoutText: String) -> String {
        if !stderrText.isEmpty { return stderrText }
        if let jsonData = stdoutText.data(using: .utf8),
           let object = try? JSONSerialization.jsonObject(with: jsonData) as? [String: Any] {
            if let message = object["message"] as? String, !message.isEmpty { return message }
            if let error = object["error"] as? String, !error.isEmpty { return error }
        }
        if !stdoutText.isEmpty { return stdoutText }
        return "fleetctl failed without an error message"
    }
}
