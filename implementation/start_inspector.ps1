$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = (Get-Command python).Source
npx -y @modelcontextprotocol/inspector $Python (Join-Path $Here "mcp_server.py")
