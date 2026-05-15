import SwiftUI

struct DashboardsView: View {
    @State private var dashboards: [AgentDashboard] = []
    @State private var selectedIndex = 0
    @State private var isLoading = true
    @State private var error: String?

    var body: some View {
        ZStack {
            Theme.bg.ignoresSafeArea()

            if isLoading {
                ProgressView()
                    .tint(Theme.amber)
            } else if dashboards.isEmpty {
                emptyState
            } else {
                VStack(spacing: 0) {
                    dashboardPicker
                        .padding(.horizontal, 20)
                        .padding(.top, 12)
                        .padding(.bottom, 8)

                    TabView(selection: $selectedIndex) {
                        ForEach(Array(dashboards.enumerated()), id: \.element.id) { index, dashboard in
                            Group {
                                if let url = dashboard.url, abs(index - selectedIndex) <= 1 {
                                    DashboardWebView(url: url)
                                        .clipShape(RoundedRectangle(cornerRadius: 16))
                                } else {
                                    RoundedRectangle(cornerRadius: 16)
                                        .fill(Theme.surface)
                                        .overlay {
                                            Text(dashboard.name)
                                                .foregroundStyle(Theme.textSecondary)
                                        }
                                }
                            }
                            .padding(.horizontal, 12)
                            .tag(index)
                        }
                    }
                    .tabViewStyle(.page(indexDisplayMode: .never))
                }
            }
        }
        .task(id: "refresh") { await fetchDashboards() }
        .onAppear { Task { await fetchDashboards() } }
    }

    // MARK: - Picker

    private var dashboardPicker: some View {
        ScrollViewReader { proxy in
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(Array(dashboards.enumerated()), id: \.element.id) { index, dashboard in
                        Button {
                            withAnimation(.easeInOut(duration: 0.25)) {
                                selectedIndex = index
                            }
                        } label: {
                            Text(dashboard.name)
                                .font(.system(size: 13, weight: selectedIndex == index ? .bold : .medium))
                                .foregroundStyle(selectedIndex == index ? Color.black : Theme.textSecondary)
                                .padding(.horizontal, 14)
                                .padding(.vertical, 7)
                                .background(
                                    selectedIndex == index ? Theme.amber : Theme.surface,
                                    in: Capsule()
                                )
                        }
                        .buttonStyle(.plain)
                        .id(index)
                    }
                }
            }
            .onChange(of: selectedIndex) { _, newValue in
                withAnimation { proxy.scrollTo(newValue, anchor: .center) }
            }
        }
    }

    // MARK: - Empty

    private var emptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "square.grid.2x2")
                .font(.system(size: 40))
                .foregroundStyle(Theme.textSecondary)
            Text("No Dashboards")
                .font(.system(size: 18, weight: .semibold))
                .foregroundStyle(Theme.textPrimary)
            Text("Ask the agent to create one")
                .font(.system(size: 14))
                .foregroundStyle(Theme.textSecondary)
            if let error {
                Text(error)
                    .font(.system(size: 12, design: .monospaced))
                    .foregroundStyle(.red.opacity(0.7))
            }
            Button("Retry") { Task { await fetchDashboards() } }
                .font(.system(size: 15, weight: .semibold))
                .foregroundStyle(Theme.amber)
                .padding(.top, 8)
        }
    }

    // MARK: - Fetch

    private func fetchDashboards() async {
        isLoading = true
        error = nil
        do {
            guard let url = URL(string: "\(Config.serverURL)/api/dashboards") else { return }
            var req = URLRequest(url: url)
            req.setValue("Bearer \(Config.apiKey)", forHTTPHeaderField: "Authorization")
            let (data, _) = try await URLSession.shared.data(for: req)
            let response = try JSONDecoder().decode(DashboardListResponse.self, from: data)
            withAnimation {
                dashboards = response.active
                isLoading = false
            }
        } catch {
            self.error = error.localizedDescription
            isLoading = false
        }
    }
}
