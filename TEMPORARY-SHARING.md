# Temporarily sharing the app from Windows

This project can be shared temporarily while it runs on your computer. The
current setup uses a Vite production preview and LocalTunnel:

```text
Your browser / manager's browser
        |
        | HTTPS temporary URL
        v
LocalTunnel -> frontend preview on port 5174
                     |
                     | /api proxy
                     v
                backend on port 8000
```

The app remains available locally as well. The development server at
`http://localhost:5714/` is separate from the production preview at
`http://localhost:5174/`; both can run at the same time. The shared URL goes
through port 5174.

## How long the URL stays available

The URL is not permanent and has no guaranteed uptime. It works only while all
of these are true:

- The backend is running on port `8000`.
- The Vite preview is running on port `5174`.
- The LocalTunnel command is still running.
- Your computer is awake and connected to the internet.

Closing the relevant terminal, restarting the computer, losing connectivity, or
a LocalTunnel outage will stop access. LocalTunnel usually assigns a new random
URL when you start a new tunnel, so share the new URL it prints. A URL may also
stop working if the tunnel provider ends the session.

## Start sharing

Use three PowerShell terminals. Keep the preview and tunnel terminals open for
as long as you want the shared URL to work.

### 1. Confirm the backend is running

The backend must already be running locally on port `8000`. Check its health
endpoint:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/health
```

The response should be HTTP 200 with `{"status":"ok"}`. If it is not running,
start it using the backend's normal project instructions before continuing.

### 2. Build the frontend

In the first terminal, change to this project's frontend directory:

```powershell
Set-Location "$HOME\Documents\python\ai-commerce-support\frontend"
npm run build
```

### 3. Start the production preview

In a second terminal, use the same frontend directory. If PowerShell is already
showing this directory in its prompt, you can skip the `Set-Location` line.

```powershell
Set-Location "$HOME\Documents\python\ai-commerce-support\frontend"
.\node_modules\.bin\vite.cmd preview --host 0.0.0.0 --port 5174 --strictPort
```

Confirm that the preview reports it is available on port `5174`. The Vite
configuration proxies `/api` requests to the local backend on port `8000`, so
the other person's browser does not try to call its own `localhost`.

### 4. Start LocalTunnel

The command below shares the production preview. To share the development
server instead, start it with:

```powershell
npm run dev -- --host 0.0.0.0
```

Then run LocalTunnel with `--port 5714` instead of `--port 5174`.

In a third PowerShell terminal:

```powershell
npx.cmd --yes localtunnel --port 5174 --local-host 127.0.0.1
```

Wait for LocalTunnel to print an HTTPS URL, then share that URL. Keep this
terminal open. LocalTunnel may first show visitors an interstitial warning page
asking them to enter the host IP displayed there before proceeding to the app.

## Verify the app

- On your computer, open `http://localhost:5714/` for the development server or
  `http://localhost:5174/` for the production preview.
- From another browser or device, open the HTTPS URL printed by LocalTunnel.
- Sign in with an authorized support account. The orders, tickets, and customer
  tabs should load through the `/api` proxy.
- If an API request fails, check that the backend is healthy on port `8000` and
  that the preview and tunnel terminals are still running.

After changing frontend code, rebuild with `npm run build` so the production
preview serves the updated bundle.

## Stop sharing

Press `Ctrl+C` in the LocalTunnel terminal and the Vite preview terminal. The
public URL will stop working. This does not stop the separate development
server on port `5714` or the backend; stop those separately only if you no
longer need them locally.

## Access and data safety

The URL is a temporary public link, not an access-control system. Anyone who
has it can reach the app's sign-in page, and the tunnel provider relays the
traffic. App authentication and backend authorization still protect support
data, but only share this demo with trusted people. Do not use this setup for
sensitive or production data, and do not tunnel backend port `8000` directly.
