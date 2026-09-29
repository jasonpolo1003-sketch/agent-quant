"""Brain Terminal: the local, read-mostly UI accepted in PROP-008.

See ``brain/_system/plan/ui_terminal_plan.md``. Everything here reads the brain
read-only. The only writes are the terminal's own database
(``db/terminal.sqlite``), the ``terminal/`` folder, and ``agent_events`` rows
through ``quant_brain.ops.events``.
"""
