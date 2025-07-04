# FastAPI Backend — Port 3001 Already In Use

## Problem
When starting the FastAPI backend, you see:
```
[Errno 98] error while attempting to bind on address ('0.0.0.0', 3001): address already in use
```
This means port 3001 is already occupied by another process.

## Resolution Steps

1. **Identify What Is Using Port 3001**

   - On **Linux/macOS**:
     ```bash
     lsof -i :3001
     ```
     or
     ```bash
     netstat -tulpn | grep 3001
     ```

   - On **Windows**:
     ```cmd
     netstat -ano | findstr :3001
     ```

   If you see a process listed, note its PID.

2. **Stop the Conflicting Process**

   - On **Linux/macOS**:
     ```bash
     kill <PID>
     ```
     If you need elevated permissions:
     ```bash
     sudo kill -9 <PID>
     ```

   - On **Windows**:
     ```cmd
     taskkill /PID <PID> /F
     ```

   > **Caution:** Only kill processes you are sure are safe to stop!

3. **Alternative: Change the FastAPI Port**

   If you don’t want to stop the other process, you can run FastAPI on a different port.
   - Open your `.env` (or wherever you define PORT).
   - Change the `PORT` entry to something like `3002` (or any free port):
     ```
     PORT=3002
     ```
   - Restart the backend.

4. **Confirm the Backend Is Running**

   After following the above:
   - Visit [http://localhost:3001/docs](http://localhost:3001/docs) (or the new port you selected) to verify the server is running.

## Why Does This Happen?

Each TCP port can only be used by one process at a time. This error means something else (another app or a forgotten instance of your backend) is already running on port 3001.

## If You Are Using Docker or Compose

Docker might be running a container on 3001. Use:
```bash
docker ps
```
to list running containers, and
```bash
docker stop <CONTAINER_ID>
```
to stop any container using the port.

---

*Once resolved, restart your FastAPI backend.*

If you continue to have trouble, share the output of the diagnostic commands above for further help.
