import SwiftUI

struct RoomDetailSheet: View {
    let room: Room
    let vm: LightsViewModel
    @Environment(\.dismiss) private var dismiss

    @State private var brightness: Double = 0
    @State private var isDragging = false

    private let namedColors: [(String, Color)] = [
        ("red", .red),
        ("orange", .orange),
        ("yellow", .yellow),
        ("green", .green),
        ("cyan", .cyan),
        ("blue", .blue),
        ("purple", .purple),
        ("pink", .pink),
        ("magenta", Color(red: 1, green: 0, blue: 1)),
        ("white", .white),
    ]

    private let colorTemps: [(String, String, Color)] = [
        ("candlelight", "Candle",   Color(red: 1.0, green: 0.6, blue: 0.2)),
        ("warm",        "Warm",     Color(red: 1.0, green: 0.75, blue: 0.4)),
        ("sunset",      "Sunset",   Color(red: 1.0, green: 0.8, blue: 0.5)),
        ("daylight",    "Day",      Color(red: 0.9, green: 0.95, blue: 1.0)),
        ("cool",        "Cool",     Color(red: 0.7, green: 0.85, blue: 1.0)),
    ]

    var body: some View {
        ZStack {
            Theme.bg.ignoresSafeArea()

            VStack(alignment: .leading, spacing: 28) {
                // Header
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(room.name)
                            .font(.system(size: 26, weight: .bold, design: .rounded))
                            .foregroundStyle(Theme.textPrimary)

                        Text("\(room.lightCount) light\(room.lightCount == 1 ? "" : "s")")
                            .font(.system(size: 13, weight: .medium))
                            .foregroundStyle(Theme.textSecondary)
                    }

                    Spacer()

                    Button {
                        Task { await vm.toggleRoom(room) }
                    } label: {
                        Image(systemName: "power")
                            .font(.system(size: 18, weight: .bold))
                            .foregroundStyle(room.on ? Color.black : Theme.textSecondary)
                            .frame(width: 52, height: 52)
                            .background(room.on ? Theme.amber : Theme.inactive)
                            .clipShape(Circle())
                            .shadow(color: room.on ? Theme.amberGlow : .clear, radius: 12)
                    }
                    .buttonStyle(.plain)
                }

                // Brightness
                VStack(alignment: .leading, spacing: 10) {
                    sectionLabel("BRIGHTNESS")

                    HStack(spacing: 16) {
                        AmberSlider(value: $brightness) { editing in
                            isDragging = editing
                            if !editing {
                                Task { await vm.setRoomBrightness(room, Int(brightness)) }
                            }
                        }

                        Text("\(Int(brightness))%")
                            .font(.system(size: 18, weight: .bold, design: .monospaced))
                            .foregroundStyle(Theme.textPrimary)
                            .frame(width: 56, alignment: .trailing)
                    }
                }

                // Colors
                VStack(alignment: .leading, spacing: 12) {
                    sectionLabel("COLOR")

                    HStack(spacing: 10) {
                        ForEach(namedColors, id: \.0) { name, color in
                            Button {
                                Task { await vm.setRoomColor(room, name) }
                            } label: {
                                Circle()
                                    .fill(color.gradient)
                                    .frame(width: 40, height: 40)
                                    .overlay(Circle().stroke(.white.opacity(0.15), lineWidth: 1))
                                    .shadow(color: color.opacity(0.3), radius: 4)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }

                // Color temperature
                VStack(alignment: .leading, spacing: 12) {
                    sectionLabel("TEMPERATURE")

                    HStack(spacing: 8) {
                        ForEach(colorTemps, id: \.0) { key, label, color in
                            Button {
                                Task { await vm.setRoomColorTemp(room, key) }
                            } label: {
                                VStack(spacing: 6) {
                                    RoundedRectangle(cornerRadius: 8)
                                        .fill(color.gradient)
                                        .frame(width: 48, height: 28)
                                    Text(label)
                                        .font(.system(size: 11, weight: .medium))
                                        .foregroundStyle(Theme.textSecondary)
                                }
                                .padding(.vertical, 8)
                                .padding(.horizontal, 6)
                                .background(Theme.surface, in: RoundedRectangle(cornerRadius: 12))
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }

                Spacer()
            }
            .padding(28)
        }
        .onAppear { brightness = Double(room.brightness) }
        .onChange(of: room.brightness) { _, v in
            if !isDragging { withAnimation { brightness = Double(v) } }
        }
    }

    private func sectionLabel(_ text: String) -> some View {
        Text(text)
            .font(.system(size: 11, weight: .bold))
            .foregroundStyle(Theme.textSecondary)
            .tracking(2.5)
    }
}
