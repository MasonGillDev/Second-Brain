import SwiftUI

struct SceneChip: View {
    let scene: LightScene
    let vm: LightsViewModel
    @State private var isActivating = false

    var body: some View {
        Button {
            guard !isActivating else { return }
            isActivating = true
            Task {
                await vm.activateScene(scene)
                try? await Task.sleep(for: .seconds(0.6))
                isActivating = false
            }
        } label: {
            HStack(spacing: 8) {
                Image(systemName: "sparkles")
                    .font(.system(size: 12))
                Text(scene.name)
                    .font(.system(size: 14, weight: .semibold, design: .rounded))
            }
            .foregroundStyle(isActivating ? Color.black : Theme.textPrimary)
            .padding(.horizontal, 20)
            .padding(.vertical, 12)
            .background(
                Capsule()
                    .fill(isActivating ? Theme.amber : Theme.surface)
            )
            .overlay(Capsule().stroke(Theme.amber.opacity(0.25), lineWidth: 1))
        }
        .buttonStyle(.plain)
        .animation(.easeInOut(duration: 0.2), value: isActivating)
    }
}
