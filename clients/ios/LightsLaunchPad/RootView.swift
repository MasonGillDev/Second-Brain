import SwiftUI

enum AppTab {
    case lights, dashboards
}

struct RootView: View {
    @StateObject private var vm = LightsViewModel()
    @State private var activeTab: AppTab = .lights
    @State private var selectedRoom: Room?
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        ZStack(alignment: .bottom) {
            // Background
            Theme.bg.ignoresSafeArea()

            // Content
            Group {
                switch activeTab {
                case .lights:
                    ContentView(vm: vm, selectedRoom: $selectedRoom)
                case .dashboards:
                    DashboardsView()
                }
            }
            .padding(.bottom, 56) // room for tab bar

            // Tab bar
            tabBar
        }
        .preferredColorScheme(.dark)
        .sheet(item: $selectedRoom) { room in
            RoomDetailSheet(room: room, vm: vm)
                .presentationDetents([.medium, .large])
                .presentationDragIndicator(.visible)
        }
        .task {
            await vm.refresh()
            vm.startPolling()
            vm.resetIdleTimer()
        }
        .onChange(of: scenePhase) { _, newPhase in
            switch newPhase {
            case .active:
                vm.onForeground()
                if activeTab != .lights { vm.stopPolling() }
            case .background, .inactive:
                vm.onBackground()
            @unknown default:
                break
            }
        }
        .onChange(of: activeTab) { oldTab, newTab in
            if newTab == .lights {
                // Returning to lights — resume polling
                vm.wake()
            } else {
                // Leaving lights — stop polling + idle timer
                vm.stopPolling()
                vm.cancelIdleTimer()
            }
        }
    }

    // MARK: - Tab Bar

    private var tabBar: some View {
        HStack(spacing: 0) {
            tabButton(.lights, icon: "lightbulb.fill", label: "Lights")
            tabButton(.dashboards, icon: "square.grid.2x2.fill", label: "Apps")
        }
        .padding(.horizontal, 24)
        .padding(.top, 10)
        .padding(.bottom, 8)
        .background {
            Theme.surface
                .ignoresSafeArea(edges: .bottom)
                .shadow(color: .black.opacity(0.3), radius: 12, y: -4)
        }
    }

    private func tabButton(_ tab: AppTab, icon: String, label: String) -> some View {
        Button {
            withAnimation(.easeInOut(duration: 0.2)) { activeTab = tab }
        } label: {
            VStack(spacing: 4) {
                Image(systemName: icon)
                    .font(.system(size: 18))
                Text(label)
                    .font(.system(size: 11, weight: .semibold))
            }
            .foregroundStyle(activeTab == tab ? Theme.amber : Theme.textSecondary)
            .frame(maxWidth: .infinity)
        }
        .buttonStyle(.plain)
    }
}
