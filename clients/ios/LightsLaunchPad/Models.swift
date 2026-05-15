import Foundation

struct Light: Codable, Identifiable, Equatable {
    let id: String
    let name: String
    let on: Bool
    let brightness: Int
    let reachable: Bool
}

struct Room: Codable, Identifiable, Equatable {
    let id: String
    let name: String
    let type: String
    let on: Bool
    let brightness: Int
    let lightCount: Int

    enum CodingKeys: String, CodingKey {
        case id, name, type, on, brightness
        case lightCount = "light_count"
    }
}

struct LightScene: Codable, Identifiable, Equatable {
    let id: String
    let name: String
    let group: String
}
