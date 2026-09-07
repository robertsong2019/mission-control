#!/usr/bin/env python3
"""Build mission-control dashboard-data.json from live system state."""
import json, subprocess, time, datetime, re, os

NOW = datetime.datetime.now(datetime.timezone.utc)
CST = datetime.timezone(datetime.timedelta(hours=8))
now_cst = NOW.astimezone(CST)
NOW_MS = int(time.time() * 1000)

def sh(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip()

# ---------- cron ----------
cron_out = sh("openclaw cron list 2>/dev/null")
KNOWN_NAMES = {
    "2c714952": "github-trending-deep-analysis",
    "1ea6e3b0": "knowledge-organization-morning",
}
cron_jobs = []
row_re = re.compile(r'^(?P<id>[0-9a-f-]{36})\s+(?P<name>\S+)\s+cron\s+(?P<rest>.*)$')
for line in cron_out.splitlines():
    m = row_re.match(line)
    if not m:
        continue
    jid_full, raw_name, rest = m.group('id'), m.group('name'), m.group('rest')
    jid = jid_full[:8]
    name = KNOWN_NAMES.get(jid, raw_name)
    rc = [c.strip() for c in re.split(r'\s{2,}', rest) if c.strip()]
    if len(rc) == 7:      # sched, next, last, status, target, agent, model
        sched, last, status = rc[0], rc[2], rc[3]
    elif len(rc) == 6:    # sched+next glued (truncated sched), last, status, target, agent, model
        sched, last, status = re.sub(r'\s+in \S+$', '', rc[0]), rc[1], rc[2]
    else:
        continue
    sched = re.sub(r'\s*\.\.\.$', '', sched.split(' @')[0].strip())
    cron_jobs.append({
        "id": jid, "fullId": jid_full, "name": name,
        "schedule": sched,
        "status": status, "lastRun": last,
    })

ok_n = sum(1 for j in cron_jobs if j["status"] == "ok")
err_n = sum(1 for j in cron_jobs if j["status"] == "error")
run_n = sum(1 for j in cron_jobs if j["status"] == "running")
err_jobs = [f'{j["id"]} ({j["name"]})' for j in cron_jobs if j["status"] == "error"]

# ---------- sessions ----------
store = json.load(open('/root/.openclaw/agents/main/sessions/sessions.json'))
sessions = []
for key, v in store.items():
    sessions.append({
        "key": key,
        "model": v.get("model") or v.get("modelOverride") or "unknown",
        "totalTokens": v.get("totalTokens") or 0,
        "updatedAtMs": v.get("updatedAt", 0),
    })
sessions.sort(key=lambda s: -s["updatedAtMs"])
active24 = [s for s in sessions if NOW_MS - s["updatedAtMs"] <= 24 * 3600 * 1000]
total_tokens_all = sum(s["totalTokens"] for s in sessions)
total_tokens_24h = sum(s["totalTokens"] for s in active24)

def ago(ms):
    d = (NOW_MS - ms) / 1000
    if d < 60: return f"{int(d)}s ago"
    if d < 3600: return f"{int(d//60)}m ago"
    if d < 86400: return f"{int(d//3600)}h ago"
    return f"{int(d//86400)}d ago"

recent = [{
    "key": s["key"],
    "label": s["key"],
    "model": s["model"],
    "totalTokens": s["totalTokens"],
    "updatedAt": ago(s["updatedAtMs"]),
} for s in sessions[:20]]

# ---------- host ----------
uptime_p = sh("uptime -p").replace("up ", "")
loadavg = sh("cat /proc/loadavg").split()[:3]
df_out = sh("df -h /").splitlines()[-1].split()
mem = {}
for line in sh("cat /proc/meminfo").splitlines():
    k, v = line.split(":")
    mem[k] = int(v.strip().split()[0])  # kB

# ---------- git ----------
ws = "/root/.openclaw/workspace"
last_commit = sh("git log -1 --format='%h %s'", cwd=ws)
recent_commits = sh("git log -6 --format='%h %s'", cwd=ws).splitlines()

data = {
    "lastUpdated": NOW.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    "generatedAt": now_cst.strftime("%Y-%m-%d %H:%M CST"),
    "system": {
        "gateway": {
            "status": "running",
            "port": 34524,
            "bind": "lan (0.0.0.0)",
            "dashboard": "http://10.8.0.5:34524/sponf0/",
            "rpcProbe": "ok",
            "nodeVersion": sh("node --version"),
            "openclawVersion": "2026.4.14"
        },
        "host": {
            "os": "Linux 6.8.0-71-generic (x64)",
            "hostname": os.uname().nodename,
            "uptime": uptime_p,
            "loadAverage": ", ".join(loadavg),
            "disk": {
                "total": df_out[1], "used": df_out[2],
                "available": df_out[3], "usage": df_out[4]
            },
            "memory": {
                "totalMB": mem["MemTotal"] // 1024,
                "usedMB": (mem["MemTotal"] - mem["MemAvailable"]) // 1024,
                "freeMB": mem["MemFree"] // 1024,
                "availableMB": mem["MemAvailable"] // 1024,
                "swapTotalMB": mem["SwapTotal"] // 1024,
                "swapUsedMB": (mem["SwapTotal"] - mem["SwapFree"]) // 1024
            }
        },
        "model": "zai/glm-5.3-flash"
    },
    "cronSummary": {
        "total": len(cron_jobs), "ok": ok_n, "error": err_n,
        "running": run_n, "errorJobs": err_jobs
    },
    "cronJobs": cron_jobs,
    "sessions": {
        "total": len(sessions),
        "unique": len(sessions),
        "active24h": len(active24),
        "totalTokens": total_tokens_all,
        "active24hTokens": total_tokens_24h,
        "recent": recent
    },
    "git": {
        "repo": "robertsong2019/openclaw-workspace",
        "lastCommit": last_commit,
        "recentCommits": recent_commits
    }
}

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "dashboard-data.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print(f"written {out}")
print(f"cron: {ok_n} ok / {err_n} error / {run_n} running / {len(cron_jobs)} total; errors: {err_jobs}")
print(f"sessions: {len(sessions)} total, {len(active24)} active-24h, tokens all={total_tokens_all}, 24h={total_tokens_24h}")
