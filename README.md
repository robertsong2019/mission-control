# Mission Control Dashboard 🚀

Real-time dashboard for monitoring OpenClaw agent activities, cron jobs, and recent activity.

## 🌐 Live Demo

**Dashboard URL**: https://robertsong2019.github.io/mission-control/

**PIN**: `1234` (change this in index.html)

## 📋 Setup Instructions

### Step 1: Enable GitHub Pages

1. Go to repository Settings → Pages
2. Source: Deploy from branch `main`
3. Folder: `/ (root)`
4. Click Save

The dashboard will be live at: `https://robertsong2019.github.io/mission-control/`

### Step 2: Change PIN Code

Edit `index.html` and find:
```javascript
const CONFIG = {
    PIN: '1234',  // Change this to your preferred PIN!
    ...
};
```

### Step 3: Auto-Update (Optional)

Create a cron job to automatically update the dashboard data:

```yaml
name: Dashboard Update
schedule: "*/30 * * * *"  # Every 30 minutes
model: sonnet
prompt: |
  Update the Mission Control dashboard:
  
  1. Run `openclaw cron list` to get job names, statuses, error counts, last run times
  2. Run `openclaw sessions list` to find active sub-agents and their tasks
  3. Build JSON matching the dashboard schema from API data only
  4. Push to GitHub
  
  Do not read local files. Only use cron list and sessions_list data.
```

## 🔒 Security Notes

- The PIN is client-side only (prevents casual access, not determined attackers)
- For stronger protection, make your GitHub repo **private** (GitHub Pro)
- Only operational status data is displayed (no credentials or sensitive info)
- All data stays on your machine (only JSON is pushed to GitHub)

## 📊 Features

- ✅ Real-time status updates (30-second polling)
- ✅ Action items with priority levels
- ✅ Active task monitoring
- ✅ Product health status
- ✅ Cron job monitoring with error tracking
- ✅ Recent activity timeline
- ✅ PIN-protected access
- ✅ Mobile-responsive design

## 🎨 Customization

Edit `index.html` to customize:
- PIN code
- Refresh interval (default: 30 seconds)
- Color scheme (CSS variables)
- Layout and sections

## 📝 Data Format

The dashboard expects JSON in this format (see `data/dashboard-data.json`):

```json
{
  "lastUpdated": "2024-01-15T12:00:00Z",
  "actionRequired": [...],
  "activeNow": [...],
  "products": [...],
  "crons": [...],
  "recentActivity": [...]
}
```

## 🔧 Manual Update

To manually update the dashboard:

1. Edit `data/dashboard-data.json`
2. Commit and push:
   ```bash
   git add data/dashboard-data.json
   git commit -m "Update dashboard data"
   git push
   ```

## 📚 Related

- [agent-dashboard skill](https://github.com/robertsong2019/mission-control) - The source skill
- [OpenClaw](https://openclaw.ai) - AI agent platform

## 📄 License

MIT

---

**Built with ❤️ for the OpenClaw community**
