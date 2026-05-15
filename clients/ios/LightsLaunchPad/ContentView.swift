import SwiftUI

struct ContentView: View {
    @ObservedObject var vm: LightsViewModel
    @Binding var selectedRoom: Room?

    private let roomColumns = [
        GridItem(.adaptive(minimum: 240, maximum: 360), spacing: 16)
    ]

    var body: some View {
        ZStack {
            // Background gradient
            LinearGradient(
                colors: [
                    Theme.bg,
                    Color(red: 0.055, green: 0.055, blue: 0.07),
                    Theme.bg,
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            VStack(spacing: 0) {
                header
                    .padding(.horizontal, 28)
                    .padding(.top, 16)
                    .padding(.bottom, 12)

                // Thin separator
                Rectangle()
                    .fill(Theme.surface)
                    .frame(height: 1)

                if vm.lights.isEmpty && !vm.isConnected {
                    Spacer()
                    connectionError
                    Spacer()
                } else {
                    mainContent
                }
            }

            // Sleep overlay
            if vm.powerState == .sleeping {
                Color.black
                    .opacity(0.93)
                    .ignoresSafeArea()
                    .transition(.opacity)
                    .onTapGesture { vm.wake() }
                    .overlay {
                        VStack(spacing: 12) {
                            Image(systemName: "moon.fill")
                                .font(.system(size: 28))
                                .foregroundStyle(Theme.textSecondary.opacity(0.6))
                            Text("Tap to wake")
                                .font(.system(size: 14, weight: .medium))
                                .foregroundStyle(Theme.textSecondary.opacity(0.6))
                        }
                    }
            }
        }
    }

    // MARK: - Header

    private var header: some View {
        HStack(spacing: 20) {
            // Title
            VStack(alignment: .leading, spacing: 3) {
                Text("LAUNCHPAD")
                    .font(.system(size: 26, weight: .heavy, design: .rounded))
                    .foregroundStyle(Theme.textPrimary)
                    .tracking(3)

                HStack(spacing: 6) {
                    Circle()
                        .fill(vm.isConnected ? Color.green : Color.red)
                        .frame(width: 6, height: 6)
                    Text(vm.isConnected
                         ? "\(vm.lights.filter(\.reachable).count) lights connected"
                         : "Disconnected")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(Theme.textSecondary)
                }
            }

            Spacer()

            // Master all toggle
            Button {
                Task { await vm.toggleAll() }
            } label: {
                HStack(spacing: 10) {
                    Text(vm.anyOn ? "ALL ON" : "ALL OFF")
                        .font(.system(size: 13, weight: .bold, design: .rounded))
                        .foregroundStyle(vm.anyOn ? Theme.amber : Theme.textSecondary)
                        .tracking(1)

                    Image(systemName: "power")
                        .font(.system(size: 13, weight: .bold))
                        .foregroundStyle(vm.anyOn ? Color.black : Theme.textSecondary)
                        .frame(width: 34, height: 34)
                        .background(vm.anyOn ? Theme.amber : Theme.inactive)
                        .clipShape(Circle())
                        .shadow(color: vm.anyOn ? Theme.amberGlow : .clear, radius: 8)
                }
                .padding(.leading, 16)
                .padding(.trailing, 4)
                .padding(.vertical, 4)
                .background(Theme.surface, in: Capsule())
            }
            .buttonStyle(.plain)
        }
    }

    // MARK: - Main scrollable content

    private var mainContent: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 28) {
                // Rooms
                sectionLabel("ROOMS")
                LazyVGrid(columns: roomColumns, spacing: 16) {
                    ForEach(vm.rooms) { room in
                        RoomCard(room: room, vm: vm) {
                            selectedRoom = room
                        }
                    }
                }

                // Scenes
                if !vm.scenes.isEmpty {
                    sectionLabel("SCENES")
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 10) {
                            ForEach(vm.scenes) { scene in
                                SceneChip(scene: scene, vm: vm)
                            }
                        }
                    }
                }

                // All lights
                sectionLabel("ALL LIGHTS")
                VStack(spacing: 1) {
                    ForEach(vm.lights) { light in
                        LightRow(light: light, vm: vm)
                    }
                }
                .clipShape(RoundedRectangle(cornerRadius: Theme.cardRadius))
            }
            .padding(24)
            .padding(.bottom, 40)
        }
    }

    // MARK: - Connection error

    private var connectionError: some View {
        VStack(spacing: 16) {
            Image(systemName: "wifi.slash")
                .font(.system(size: 40))
                .foregroundStyle(Theme.textSecondary)
            Text("Cannot reach server")
                .font(.system(size: 18, weight: .semibold))
                .foregroundStyle(Theme.textPrimary)
            Text(Config.serverURL)
                .font(.system(size: 14, weight: .medium, design: .monospaced))
                .foregroundStyle(Theme.textSecondary)
            Button("Retry") {
                Task { await vm.refresh() }
            }
            .font(.system(size: 15, weight: .semibold))
            .foregroundStyle(Theme.amber)
            .padding(.top, 8)
        }
    }

    // MARK: - Helpers

    private func sectionLabel(_ text: String) -> some View {
        Text(text)
            .font(.system(size: 12, weight: .bold))
            .foregroundStyle(Theme.textSecondary)
            .tracking(3)
    }
}

#Preview {
    RootView()
}
