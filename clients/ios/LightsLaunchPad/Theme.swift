import SwiftUI

enum Theme {
    // Surfaces
    static let bg = Color(red: 0.047, green: 0.047, blue: 0.055)
    static let surface = Color(red: 0.098, green: 0.098, blue: 0.114)
    static let surfaceRaised = Color(red: 0.137, green: 0.137, blue: 0.153)

    // Accent — warm amber
    static let amber = Color(red: 0.96, green: 0.65, blue: 0.14)
    static let amberGlow = Color(red: 0.96, green: 0.65, blue: 0.14).opacity(0.35)

    // Text
    static let textPrimary = Color(red: 0.94, green: 0.93, blue: 0.90)
    static let textSecondary = Color(red: 0.42, green: 0.42, blue: 0.46)

    // Inactive elements
    static let inactive = Color(red: 0.176, green: 0.176, blue: 0.196)

    // Layout
    static let cardRadius: CGFloat = 20
}
