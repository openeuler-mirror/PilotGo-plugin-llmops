#!/usr/bin/env python3
"""Test MCP protocol communication with the timeserver."""

import json
import subprocess
import sys
import time

def test_mcp_protocol():
    """Test MCP protocol communication."""
    print("🧪 Testing MCP Protocol Communication...")
    
    # Start the server process using direct Python execution
    cmd = [
        "/data/usershare/project/kyaiops-demo/agno-uv-project/.venv/bin/python",
        "/data/usershare/project/kyaiops-demo/agno-uv-project/app/extensions/mcp/weather-main/weather.py"
    ]
    
    try:
        # Start the server
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print("✅ Server process started")
        
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        
        print("📤 Sending initialize request...")
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        
        # Read response
        response_line = process.stdout.readline()
        if response_line:
            response = json.loads(response_line.strip())
            print(f"📥 Initialize response: {response.get('result', {}).get('serverInfo', {}).get('name', 'Unknown')}")
        
        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        print("📤 Sending initialized notification...")
        process.stdin.write(json.dumps(initialized_notification) + "\n")
        process.stdin.flush()
        
        # Send tools/list request
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        print("📤 Sending tools/list request...")
        process.stdin.write(json.dumps(tools_request) + "\n")
        process.stdin.flush()
        
        # Read tools response
        tools_response_line = process.stdout.readline()
        if tools_response_line:
            tools_response = json.loads(tools_response_line.strip())
            tools = tools_response.get('result', {}).get('tools', [])
            print(f"📥 Found {len(tools)} tools:")
            for tool in tools:
                print(f"   - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')[:50]}...")
        
        # Clean up
        process.terminate()
        process.wait(timeout=5)
        
        return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        if 'process' in locals():
            process.terminate()
        return False

if __name__ == "__main__":
    success = test_mcp_protocol()
    sys.exit(0 if success else 1) 