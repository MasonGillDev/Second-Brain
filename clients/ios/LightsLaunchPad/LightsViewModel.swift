import SwiftUI

enum AppPowerState {
    case active, sleeping
}

@MainActor
class LightsViewModel: ObservableObject {
    @Published var lights: [Light] = []
    @Published var rooms: [Room] = []
    @Published var scenes: [LightScene] = []
    @Published var isConnected = false
    @Published var powerState: AppPowerState = .active

    private let api = LightAPI.shared
    private var pollTask: Task<Void, Never>?
    private var idleTask: Task<Void, Never>?
    private var refreshDebounce: Task<Void, Never>?

    private let idleTimeout: TimeInterval = 45

    var anyOn: Bool { rooms.contains { $0.on } || lights.contains { $0.on } }

    // MARK: - Refresh

    func refresh() async {
        do {
            async let l = api.fetchLights()
            async let r = api.fetchRooms()
            async let s = api.fetchScenes()
            let (newLights, newRooms, newScenes) = try await (l, r, s)
            withAnimation(.easeInOut(duration: 0.25)) {
                lights = newLights
                rooms = newRooms
                scenes = newScenes
                isConnected = true
            }
        } catch {
            withAnimation { isConnected = false }
        }
    }

    /// Schedule a single refresh after a delay (debounced).
    /// Used after mutations so the UI reconciles with actual state.
    private func scheduleRefresh(delay: TimeInterval = 4) {
        refreshDebounce?.cancel()
        refreshDebounce = Task {
            try? await Task.sleep(for: .seconds(delay))
            guard !Task.isCancelled else { return }
            await refresh()
        }
    }

    // MARK: - Polling (active state only)

    func startPolling() {
        pollTask?.cancel()
        pollTask = Task {
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(4))
                guard !Task.isCancelled else { break }
                await refresh()
            }
        }
    }

    func stopPolling() {
        pollTask?.cancel()
        pollTask = nil
    }

    // MARK: - Sleep / Wake

    func wake() {
        guard powerState == .sleeping else {
            resetIdleTimer()
            return
        }
        withAnimation(.easeOut(duration: 0.4)) { powerState = .active }
        Task { await refresh() }
        startPolling()
        resetIdleTimer()
    }

    func sleep() {
        stopPolling()
        withAnimation(.easeIn(duration: 0.6)) { powerState = .sleeping }
    }

    func resetIdleTimer() {
        idleTask?.cancel()
        idleTask = Task {
            try? await Task.sleep(for: .seconds(idleTimeout))
            guard !Task.isCancelled else { return }
            sleep()
        }
    }

    func cancelIdleTimer() {
        idleTask?.cancel()
        idleTask = nil
    }

    /// Call when app enters foreground
    func onForeground() {
        withAnimation { powerState = .active }
        Task { await refresh() }
        startPolling()
        resetIdleTimer()
    }

    /// Call when app enters background
    func onBackground() {
        stopPolling()
        idleTask?.cancel()
    }

    // MARK: - Interaction tracking

    /// Wraps any user-initiated action: resets idle timer + schedules post-mutation refresh
    private func userAction() {
        resetIdleTimer()
        scheduleRefresh()
    }

    // MARK: - Optimistic helpers

    private func updateRoom(_ room: Room, on: Bool? = nil, brightness: Int? = nil) {
        if let i = rooms.firstIndex(where: { $0.id == room.id }) {
            rooms[i] = Room(
                id: room.id, name: room.name, type: room.type,
                on: on ?? room.on,
                brightness: brightness ?? room.brightness,
                lightCount: room.lightCount
            )
        }
    }

    private func updateLight(_ light: Light, on: Bool? = nil, brightness: Int? = nil) {
        if let i = lights.firstIndex(where: { $0.id == light.id }) {
            lights[i] = Light(
                id: light.id, name: light.name,
                on: on ?? light.on,
                brightness: brightness ?? light.brightness,
                reachable: light.reachable
            )
        }
    }

    private func fire(_ work: @escaping () async throws -> Void) {
        Task { try? await work() }
    }

    // MARK: - Room controls

    func toggleRoom(_ room: Room) {
        let newOn = !room.on
        withAnimation { updateRoom(room, on: newOn, brightness: newOn ? max(room.brightness, 100) : 0) }
        fire { try await self.api.setRoom(room.name, on: newOn) }
        userAction()
    }

    func setRoomBrightness(_ room: Room, _ value: Int) {
        withAnimation { updateRoom(room, on: value > 0, brightness: value) }
        fire { try await self.api.setRoom(room.name, brightness: value) }
        userAction()
    }

    func setRoomColor(_ room: Room, _ color: String) {
        fire { try await self.api.setRoom(room.name, color: color) }
        userAction()
    }

    func setRoomColorTemp(_ room: Room, _ temp: String) {
        fire { try await self.api.setRoom(room.name, colorTemp: temp) }
        userAction()
    }

    // MARK: - Individual light controls

    func toggleLight(_ light: Light) {
        let newOn = !light.on
        withAnimation { updateLight(light, on: newOn, brightness: newOn ? max(light.brightness, 100) : 0) }
        fire { try await self.api.setLight(light.id, on: newOn) }
        userAction()
    }

    func setLightBrightness(_ light: Light, _ value: Int) {
        withAnimation { updateLight(light, on: value > 0, brightness: value) }
        fire { try await self.api.setLight(light.id, brightness: value) }
        userAction()
    }

    func setLightColor(_ light: Light, _ color: String) {
        fire { try await self.api.setLight(light.id, color: color) }
        userAction()
    }

    func setLightColorTemp(_ light: Light, _ temp: String) {
        fire { try await self.api.setLight(light.id, colorTemp: temp) }
        userAction()
    }

    // MARK: - Master controls

    func toggleAll() {
        let newOn = !anyOn
        withAnimation {
            for i in rooms.indices {
                rooms[i] = Room(
                    id: rooms[i].id, name: rooms[i].name, type: rooms[i].type,
                    on: newOn,
                    brightness: newOn ? max(rooms[i].brightness, 100) : 0,
                    lightCount: rooms[i].lightCount
                )
            }
            for i in lights.indices where lights[i].reachable {
                lights[i] = Light(
                    id: lights[i].id, name: lights[i].name,
                    on: newOn,
                    brightness: newOn ? max(lights[i].brightness, 100) : 0,
                    reachable: true
                )
            }
        }
        fire { try await self.api.setAll(on: newOn) }
        userAction()
    }

    func setAllBrightness(_ value: Int) {
        fire { try await self.api.setAll(brightness: value) }
        userAction()
    }

    func activateScene(_ scene: LightScene) {
        fire { try await self.api.activateScene(scene.name) }
        userAction()
    }
}
