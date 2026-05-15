import Foundation

struct AgentDashboard: Codable, Identifiable, Equatable {
    let slug: String
    let name: String
    let description: String?
    let hasApi: Bool?
    let hasData: Bool?

    var id: String { slug }

    var url: URL? {
        URL(string: "\(Config.serverURL)/d/\(slug)/")
    }

    enum CodingKeys: String, CodingKey {
        case slug, name, description
        case hasApi = "has_api"
        case hasData = "has_data"
    }
}

struct DashboardListResponse: Codable {
    let active: [AgentDashboard]
    let archived: [AgentDashboard]
}
