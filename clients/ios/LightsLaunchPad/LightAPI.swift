import Foundation

actor LightAPI {
    static let shared = LightAPI()

    private let session: URLSession = {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 10
        return URLSession(configuration: config)
    }()

    // MARK: - Generic helpers

    private func request<T: Decodable>(_ path: String, method: String = "GET",
                                        body: [String: Any]? = nil) async throws -> T {
        guard let url = URL(string: Config.serverURL + path) else {
            throw URLError(.badURL)
        }
        var req = URLRequest(url: url)
        req.httpMethod = method
        req.setValue("Bearer \(Config.apiKey)", forHTTPHeaderField: "Authorization")
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let body {
            req.httpBody = try JSONSerialization.data(withJSONObject: body)
        }
        let (data, _) = try await session.data(for: req)
        return try JSONDecoder().decode(T.self, from: data)
    }

    private func fire(_ path: String, method: String, body: [String: Any]) async throws {
        guard let url = URL(string: Config.serverURL + path) else { return }
        var req = URLRequest(url: url)
        req.httpMethod = method
        req.setValue("Bearer \(Config.apiKey)", forHTTPHeaderField: "Authorization")
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: body)
        _ = try await session.data(for: req)
    }

    // MARK: - Response wrappers

    private struct LightsResponse: Decodable { let lights: [Light] }
    private struct RoomsResponse: Decodable { let rooms: [Room] }
    private struct ScenesResponse: Decodable { let scenes: [LightScene] }

    // MARK: - Fetch

    func fetchLights() async throws -> [Light] {
        let r: LightsResponse = try await request("/api/lights")
        return r.lights
    }

    func fetchRooms() async throws -> [Room] {
        let r: RoomsResponse = try await request("/api/lights/rooms")
        return r.rooms
    }

    func fetchScenes() async throws -> [LightScene] {
        let r: ScenesResponse = try await request("/api/lights/scenes")
        return r.scenes
    }

    // MARK: - Control

    func setLight(_ id: String, on: Bool? = nil, brightness: Int? = nil,
                  color: String? = nil, colorTemp: String? = nil) async throws {
        var body: [String: Any] = [:]
        if let on { body["on"] = on }
        if let brightness { body["brightness"] = brightness }
        if let color { body["color"] = color }
        if let colorTemp { body["color_temp"] = colorTemp }
        try await fire("/api/lights/\(id)", method: "PUT", body: body)
    }

    func setRoom(_ name: String, on: Bool? = nil, brightness: Int? = nil,
                 color: String? = nil, colorTemp: String? = nil) async throws {
        var body: [String: Any] = [:]
        if let on { body["on"] = on }
        if let brightness { body["brightness"] = brightness }
        if let color { body["color"] = color }
        if let colorTemp { body["color_temp"] = colorTemp }
        let encoded = name.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? name
        try await fire("/api/lights/room/\(encoded)", method: "PUT", body: body)
    }

    func setAll(on: Bool? = nil, brightness: Int? = nil,
                color: String? = nil, colorTemp: String? = nil) async throws {
        var body: [String: Any] = [:]
        if let on { body["on"] = on }
        if let brightness { body["brightness"] = brightness }
        if let color { body["color"] = color }
        if let colorTemp { body["color_temp"] = colorTemp }
        try await fire("/api/lights/all", method: "PUT", body: body)
    }

    func activateScene(_ name: String) async throws {
        try await fire("/api/lights/scene", method: "POST", body: ["scene_name": name])
    }
}
