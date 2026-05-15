import SwiftUI

@main
struct LightsLaunchPadApp: App {
    var body: some SwiftUI.Scene {
        WindowGroup {
            RootView()
                .onAppear {
                    UIApplication.shared.isIdleTimerDisabled = true
                }
        }
    }
}
