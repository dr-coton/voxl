# Live macOS display selection

Allow an authenticated viewer, including an iPad, to select an attached Mac display
without restarting voxl or changing its URL.

- Use one shared active display; all connected viewers follow the selection.
- Show the display picker only when a Mac reports multiple displays.
- Refuse display changes from read-only viewers.
- Drain and release old input before changing the capture geometry; reject input
  until each viewer acknowledges the new display generation.
- Rebuild capture, encoding and decoder state, including for equal-size displays.
- Recover to the previous display when the requested display becomes unavailable.
- Preserve the existing authentication, origin checks and file-transfer boundaries.
- Keep the current installation available while developing and testing the fork.
