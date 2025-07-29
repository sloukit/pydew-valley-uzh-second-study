# Known Issues And/Or Refused Ideas

This file contains:
 - Issues that were found but that won't be fixed.
 - Issues linked to game states that aren't achievable without modifying game conditions. (i. e. Cheat Engine, changing values in the code before executing, not respecting the rules.)
 - Issues linked to incorrect dependencies or linked to a wrong interpreter.
 - Propositions that were refused.
 - Propositions that were put aside for a late version.

Before posting a [new issue (in the issues tab of the Github repo)](https://github.com/sloukit/pydew-valley-uzh-second-study/issues), please check that it wasn't already added to this document's [Issues Section](#issues).

Before posting a [new feature request (in the issues tab of the Github repo)](https://github.com/sloukit/pydew-valley-uzh-second-study/issues), please check that it wasn't already added to this document's [Features Section](#features).

## Issues

### Manually activating Volcano causes crashing

To see more information, check [#84](https://github.com/sloukit/pydew-valley-uzh-second-study/issues/84)

Typical output log on Windows:
```py
Traceback (most recent call last):
  File "C:\Users\{username}\Documents\Github\pydew-valley-uzh-second-study\main.py", line 1166, in <module>
    asyncio.run(game.run())
  File "C:\Users\{username}\AppData\Roaming\uv\python\cpython-3.12.9-windows-x86_64-none\Lib\asyncio\runners.py", line 195, in run
    return runner.run(main)
           ^^^^^^^^^^^^^^^^
  File "C:\Users\{username}\AppData\Roaming\uv\python\cpython-3.12.9-windows-x86_64-none\Lib\asyncio\runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\{username}\AppData\Roaming\uv\python\cpython-3.12.9-windows-x86_64-none\Lib\asyncio\base_events.py", line 691, in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
  File "C:\Users\{username}\Documents\Github\pydew-valley-uzh-second-study\main.py", line 983, in run
    self.level.update(dt, self.current_state == GameState.PLAY)
  File "C:\Users\{username}\Documents\Github\pydew-valley-uzh-second-study\src\screens\level.py", line 1430, in update
    self.volcano_animation()
  File "C:\Users\{username}\Documents\Github\pydew-valley-uzh-second-study\src\screens\level.py", line 1173, in volcano_animation
    self.intro_shown.pop(Map.VOLCANO)
KeyError: <Map.VOLCANO: 'volcano'>
```

**Reason of Refusal:** This state is only achievable in debug mode.

### Apply Damage function returns AttributeError

Typical output log on Windows:
```py
Traceback (most recent call last):
  File "c:\Users\{username}\Documents\Github\pydew-valley-uzh-second-study\main.py", line 1154, in <module>
    asyncio.run(game.run())
  File "C:\Users\{username}\AppData\Roaming\uv\python\cpython-3.12.9-windows-x86_64-none\Lib\asyncio\runners.py", line 195, in run
    return runner.run(main)
           ^^^^^^^^^^^^^^^^
  File "C:\Users\{username}\AppData\Roaming\uv\python\cpython-3.12.9-windows-x86_64-none\Lib\asyncio\runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\{username}\AppData\Roaming\uv\python\cpython-3.12.9-windows-x86_64-none\Lib\asyncio\base_events.py", line 691, in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
  File "c:\Users\{username}\Documents\Github\pydew-valley-uzh-second-study\main.py", line 972, in run
    self.level.update(dt, self.current_state == GameState.PLAY)
  File "c:\Users\{username}\Documents\Github\pydew-valley-uzh-second-study\src\screens\level.py", line 1383, in update        
    self.handle_controls()
  File "c:\Users\{username}\Documents\Github\pydew-valley-uzh-second-study\src\screens\level.py", line 755, in handle_controls    self.overlay.health_bar.apply_damage(1)
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'HealthProgressBar' object has no attribute 'apply_damage'
```
This happens on token `000` when the player presses `pygame.K_2`.

**Reason of Refusal:** This state is only achievable in debug mode.

### Apply Health function returns AttributeError

Typical output log on Windows:
```py
Traceback (most recent call last):
  File "c:\Users\{username}\Documents\Github\pydew-valley-uzh-second-study\main.py", line 1154, in <module>
    asyncio.run(game.run())
  File "C:\Users\{username}\AppData\Roaming\uv\python\cpython-3.12.9-windows-x86_64-none\Lib\asyncio\runners.py", line 195, in run
    return runner.run(main)
           ^^^^^^^^^^^^^^^^
  File "C:\Users\{username}\AppData\Roaming\uv\python\cpython-3.12.9-windows-x86_64-none\Lib\asyncio\runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\{username}\AppData\Roaming\uv\python\cpython-3.12.9-windows-x86_64-none\Lib\asyncio\base_events.py", line 691, in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
  File "c:\Users\{username}\Documents\Github\pydew-valley-uzh-second-study\main.py", line 972, in run
    self.level.update(dt, self.current_state == GameState.PLAY)
  File "c:\Users\{username}\Documents\Github\pydew-valley-uzh-second-study\src\screens\level.py", line 1383, in update        
    self.handle_controls()
  File "c:\Users\{username}\Documents\Github\pydew-valley-uzh-second-study\src\screens\level.py", line 752, in handle_controls    self.overlay.health_bar.apply_health(1)
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'HealthProgressBar' object has no attribute 'apply_health'
```

This happens on token `000` when the player presses `pygame.K_1`.

**Reason of Refusal:** This state is only achievable in debug mode.

## Features

*Rejected features or Delayed Features will appear here*
