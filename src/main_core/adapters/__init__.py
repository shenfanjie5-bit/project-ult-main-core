"""Public adapters that expose main-core surfaces to other modules.

Each adapter is a *consumer-facing* boundary: other modules import these
symbols via ``main_core.adapters.<name>`` to avoid reaching into private
package internals (which violates main-core/CLAUDE.md "L1-L8 是同一项目内
的强 package 边界").
"""
