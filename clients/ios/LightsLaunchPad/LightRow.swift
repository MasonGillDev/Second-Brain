import SwiftUI

struct LightRow: View {
    let light: Light
    let vm: LightsViewModel

    @State private var sliderValue: Double = 0
    @State private var isDragging = false

    var body: some View {
        HStack(spacing: 14) {
            // Status dot
            Circle()
                .fill(light.on ? Theme.amber : Theme.inactive)
                .frame(width: 8, height: 8)
                .shadow(color: light.on ? Theme.amberGlow : .clear, radius: 4)

            // Name
            VStack(alignment: .leading, spacing: 1) {
                Text(light.name)
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(light.reachable ? Theme.textPrimary : Theme.textSecondary)
                if !light.reachable {
                    Text("Unreachable")
                        .font(.system(size: 10, weight: .medium))
                        .foregroundStyle(.red.opacity(0.6))
                }
            }
            .frame(minWidth: 140, alignment: .leading)

            // Slider
            AmberSlider(value: $sliderValue) { editing in
                isDragging = editing
                if !editing {
                    Task { await vm.setLightBrightness(light, Int(sliderValue)) }
                }
            }

            Text("\(Int(sliderValue))%")
                .font(.system(size: 12, weight: .semibold, design: .monospaced))
                .foregroundStyle(Theme.textSecondary)
                .frame(width: 38, alignment: .trailing)

            // Toggle
            Button {
                Task { await vm.toggleLight(light) }
            } label: {
                Image(systemName: "power")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(light.on ? Color.black : Theme.textSecondary)
                    .frame(width: 32, height: 32)
                    .background(light.on ? Theme.amber : Theme.inactive)
                    .clipShape(Circle())
            }
            .buttonStyle(.plain)
            .disabled(!light.reachable)
            .opacity(light.reachable ? 1 : 0.4)
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 12)
        .background(Theme.surface)
        .onAppear { sliderValue = Double(light.brightness) }
        .onChange(of: light.brightness) { _, v in
            if !isDragging { withAnimation(.easeOut(duration: 0.2)) { sliderValue = Double(v) } }
        }
    }
}
