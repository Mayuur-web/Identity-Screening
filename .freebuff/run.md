# Parakh Seva Frontend — Run Doc

## Reproduce Uncommitted Artifacts

No env files or special artifacts needed. All dependencies are in `frontend/package.json`.

From the worktree root, install dependencies:

```bash
cd frontend
npm install
```

## Run the Dev Server

```bash
cd frontend
npm run dev
```

This starts Vite on **port 5173** (default). The app serves at `http://localhost:5173/`.

### Windows Detach (PowerShell)

```powershell
powershell -NoProfile -Command "(Start-Process -FilePath 'npm.cmd' -ArgumentList 'run','dev' -WorkingDirectory '<worktree>\frontend' -RedirectStandardOutput '<log>' -RedirectStandardError '<log>.err' -WindowStyle Hidden -PassThru).Id"
```

- Use `npm.cmd` (not `npm`) — `Start-Process` doesn't resolve shell shims.
- stdout and stderr must go to **different** files; PowerShell fails if both point at one path.

### Verify

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/
# Should return 200
```
