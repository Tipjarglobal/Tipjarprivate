module.exports = {
  apps: [
    {
      name: "tipjar-backend",
      cwd: "/root/Tipjarprivate/backend",
      script: "uvicorn",
      args: "server:app --host 0.0.0.0 --port 8000",
      interpreter: "python3",
      autorestart: true,
      watch: false
    },
    {
      name: "tipjar",
      cwd: "/root/Tipjarprivate/frontend",
      script: "npx",
      args: "vite preview --host 0.0.0.0 --port 3000 --strictPort",
      autorestart: true,
      watch: false
    }
  ]
}
