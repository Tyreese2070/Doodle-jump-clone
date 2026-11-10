# Doodle-jump-clone (Jumping Man)
Claude Test

A-Level Computer Science Project, since reworked into a more polished endless climber.
Requires Python 3 with `pygame` or `pygame-ce` (`pip install pygame-ce`).

Usage:
Run `Computing Coursework - Finished/main.py`. The original coursework version is kept as `main_original.py`.

## Controls
- A / D or Left / Right arrows (or a gamepad stick / d-pad) to move
- Walk off one side of the screen to wrap round to the other side
- Esc or P to pause (the game also pauses itself when the window loses focus)
- F11 toggles fullscreen, F3 toggles the FPS counter
- Menus work with the mouse, or with Up / Down and Enter

## Features
- Smooth physics on a fixed 60 Hz timestep, with acceleration, friction, squash and stretch, and tilt
- Difficulty ramps up with height: gaps widen, platforms shrink, and more special platforms appear
- Platforms: normal, moving, vanishing (one bounce only) and crumbling (they break under you). Some have springs
- Enemies: hovering and flying spikeballs. Stomp them from above for bonus points
- Power-ups: Apple (combo multiplier up to x5), Rocket, Shield (saves you from one fall), Magnet (pulls in apples)
- The sky changes from day to sunset to night to space as you climb. Clouds and stars scroll with parallax
- Effects: particles, screen shake, floating score popups, afterimage trails, a milestone banner every 500m, and a line marking your best height
- Game-over screen with a count-up score and stats. Top-10 scores ask for your name and are saved to the leaderboard
- Options: sound volume, screen shake, particle level, fullscreen and FPS counter, all saved between sessions
- Menus play a self-running demo of the game in the background
- Saves to `save.json`. Your old `leaderboard.txt` scores are carried over automatically the first time you run the game
- All text uses pygame's built-in font, so it lines up the same on every screen (this fixes the old misaligned-text issue)
