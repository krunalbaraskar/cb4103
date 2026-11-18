# Scheduled end-to-end project worker

The Windows Scheduled Task `COR-SMOR-EndToEnd-20261115-0745` starts at **07:45 AM India Standard Time on 15 November 2026**, after the user's requested 07:44 AM threshold. This is a one-time scheduled project run, not a daily cron job.

The task launches a hidden PowerShell supervisor, which invokes the installed, authenticated Codex CLI against this workspace. It follows `project-worker-prompt.md` and the project plan to implement the analysis, process the real trajectory, validate results, and create the final report and presentation. It runs with the current user's interactive session and a workspace-write sandbox, with network access for dependencies and research. It does not require keeping the chat tab open.

**Keep this laptop powered on, awake, signed in, and connected to the internet.** A wake request and start-when-available behavior are configured, but a powered-off machine or unavailable user session cannot execute a local scheduled task. Codex account access must remain valid. Do not edit the same analysis files concurrently once the worker starts.

## Status and output

- `status.json`: scheduled/running/complete/blocked/failed state and latest heartbeat.
- `logs/*.events.jsonl`: worker activity and tool events.
- `logs/*.stderr.log`: CLI errors and diagnostics.
- `latest-result.json`: most recent structured worker outcome.
- `../WORK_LOG.md`: scientific implementation progress after work starts.
- `../reports/`: final report and presentation after completion.
- `../results/` and `../figures/`: measured outputs and validation.

The supervisor runs up to twelve sequential checkpointed invocations if needed, stops after three consecutive execution errors, and checks required artifacts plus the validation flag before accepting a `complete` result. It reports genuine blockers or failures instead of claiming success. The scheduler action has a three-day execution limit. These recovery limits do not establish that the scientific work has completed.

## Inspect or stop the task

Run these PowerShell commands from the project folder:

```powershell
Get-ScheduledTask -TaskName 'COR-SMOR-EndToEnd-20261115-0745'
Get-ScheduledTaskInfo -TaskName 'COR-SMOR-EndToEnd-20261115-0745'
Get-Content -LiteralPath '.\automation\status.json'
```

To stop an active run and prevent future starts:

```powershell
Stop-ScheduledTask -TaskName 'COR-SMOR-EndToEnd-20261115-0745'
Disable-ScheduledTask -TaskName 'COR-SMOR-EndToEnd-20261115-0745'
```

To resume from project checkpoints after the scheduled start, inspect the existing status/logs, ensure no prior worker is running, and run:

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File '.\automation\Run-ProjectWorker.ps1'
```

Configuration-only validation, without model calls or project implementation:

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File '.\automation\Run-ProjectWorker.ps1' -ValidateOnly
```
