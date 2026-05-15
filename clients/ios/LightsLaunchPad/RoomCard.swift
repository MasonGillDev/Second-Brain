import SwiftUI

struct RoomCard: View {
    let room: Room
    let vm: LightsViewModel
    var onTap: () -> Void = {}

    @State private var sliderValue: Double = 0
    @State private var isDragging = false

    private var icon: String {
        let n = room.name.lowercased()
        if n.contains("living") { return "sofa.fill" }
        if n.contains("kitchen") { return "fork.knife" }
        if n.contains("bed")     { return "bed.double.fill" }
        if n.contains("bath")    { return "shower.fill" }
        if n.contains("office")  { return "desktopcomputer" }
        if n.contains("music")   { return "music.note" }
        if n.contains("couch")   { return "sofa.fill" }
        if n.contains("dining")  { return "cup.and.saucer.fill" }
        return "lightbulb.fill"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            // Header row
            HStack(spacing: 12) {
                Image(systemName: icon)
                    .font(.system(size: 22, weight: .medium))
                    .foregroundStyle(room.on ? Theme.amber : Theme.textSecondary)
                    .frame(width: 28)

                VStack(alignment: .leading, spacing: 2) {
                    Text(room.name)
                        .font(.system(size: 17, weight: .semibold, design: .rounded))
                        .foregroundStyle(Theme.textPrimary)

                    Text("\(room.lightCount) light\(room.lightCount == 1 ? "" : "s")")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(Theme.textSecondary)
                }

                Spacer()

                // Power toggle
                Button {
                    Task { await vm.toggleRoom(room) }
                } label: {
                    Image(systemName: "power")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundStyle(room.on ? Color.black : Theme.textSecondary)
                        .frame(width: 40, height: 40)
                        .background(room.on ? Theme.amber : Theme.inactive)
                        .clipShape(Circle())
                        .shadow(color: room.on ? Theme.amberGlow : .clear, radius: 10)
                }
                .buttonStyle(.plain)
            }

            // Brightness slider
            HStack(spacing: 10) {
                Image(systemName: "sun.min")
                    .font(.system(size: 11))
                    .foregroundStyle(Theme.textSecondary)

                AmberSlider(value: $sliderValue) { editing in
                    isDragging = editing
                    if !editing {
                        Task { await vm.setRoomBrightness(room, Int(sliderValue)) }
                    }
                }

                Image(systemName: "sun.max.fill")
                    .font(.system(size: 13))
                    .foregroundStyle(room.on ? Theme.amber.opacity(0.7) : Theme.textSecondary)

                Text("\(Int(sliderValue))%")
                    .font(.system(size: 12, weight: .semibold, design: .monospaced))
                    .foregroundStyle(Theme.textSecondary)
                    .frame(width: 38, alignment: .trailing)
            }
        }
        .padding(20)
        .background(
            RoundedRectangle(cornerRadius: Theme.cardRadius)
                .fill(Theme.surface)
                .overlay(
                    RoundedRectangle(cornerRadius: Theme.cardRadius)
                        .stroke(
                            room.on
                                ? LinearGradient(
                                    colors: [Theme.amber.opacity(0.5), Theme.amber.opacity(0.05)],
                                    startPoint: .top, endPoint: .bottom)
                                : LinearGradient(colors: [.clear], startPoint: .top, endPoint: .bottom),
                            lineWidth: 1
                        )
                )
        )
        .contentShape(RoundedRectangle(cornerRadius: Theme.cardRadius))
        .onTapGesture { onTap() }
        .onAppear { sliderValue = Double(room.brightness) }
        .onChange(of: room.brightness) { _, v in
            if !isDragging { withAnimation(.easeOut(duration: 0.2)) { sliderValue = Double(v) } }
        }
    }
}
