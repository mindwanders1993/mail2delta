# Databricks Job Profiling Agent - Project Plan

## Objective
Build a "God Level" Autonomous Job Profiling Agent in an air-gapped Databricks Workspace using Genie Code capabilities. The Agent will analyze job runs, task metrics, and Spark UI bottlenecks.

## Phase 1: The Knowledge Injector (Current Phase)
Since the Databricks Workspace is disconnected, the Agent cannot dynamically search for Databricks SDK syntax or Spark REST API patterns.
**Action:** We generate Markdown cheatsheets locally. The user manually creates these files inside the Databricks workspace (e.g., in a Unity Catalog Volume) for the Agent to reference.
**Artifacts:**
- `profiling_cheatsheet.md` (Complete)

## Phase 2: The Native Tools
Instead of rigid scripts, the Agent is given generic tools to execute code based on the patterns it reads in the cheatsheets.
**Action:** Define the Python execution tool.
**Artifacts:**
- `python_executor_tool.py` (Pending)

## Phase 3: The System Prompt (Persona)
The Agent's brain. We instruct it to operate as a Plan-and-Solve agent. It must read the cheatsheet, formulate an execution graph, and execute the Python tools dynamically.
**Action:** Draft the Genie System Instructions.
**Artifacts:**
- `genie_system_prompt.md` (Pending)
