import SwiftUI

struct AmberSlider: View {
    @Binding var value: Double
    var onEditingChanged: (Bool) -> Void = { _ in }

    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width
            let frac = min(max(value / 100, 0), 1)

            ZStack(alignment: .leading) {
                // Track
                Capsule()
                    .fill(Theme.inactive)
                    .frame(height: 6)

                // Fill
                Capsule()
                    .fill(
                        LinearGradient(
                            colors: [Theme.amber.opacity(0.35), Theme.amber],
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
                    .frame(width: max(6, frac * w), height: 6)

                // Thumb
                Circle()
                    .fill(Theme.amber)
                    .frame(width: 22, height: 22)
                    .shadow(color: Theme.amberGlow, radius: 8)
                    .offset(x: max(0, frac * w - 11))
            }
            .contentShape(Rectangle())
            .gesture(
                DragGesture(minimumDistance: 0)
                    .onChanged { drag in
                        let f = min(max(drag.location.x / w, 0), 1)
                        value = f * 100
                        onEditingChanged(true)
                    }
                    .onEnded { _ in
                        onEditingChanged(false)
                    }
            )
        }
        .frame(height: 28)
    }
}
