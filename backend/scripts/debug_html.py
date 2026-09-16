#!/usr/bin/env python3
"""Debug script to see raw HTML from CTPB."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

async def main():
    url = "https://ctpb.euskalpilota.fr/resultats.php"
    
    post_data = "InSel=&InCompet=20260104&InSpec=0&InVille=&InClub=&InDate=&InDatef=&InCat=0&InPhase=0&InVoir=Voir+les+r%C3%A9sultats"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://ctpb.euskalpilota.fr",
        "Referer": "https://ctpb.euskalpilota.fr/resultats.php",
    }
    
    async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=headers) as client:
        print("📡 Getting session cookie...")
        await client.get(url)
        
        print("📡 POSTing form data...")
        response = await client.post(url, content=post_data)
        
        print(f"\n📊 Status: {response.status_code}")
        print(f"📊 Content-Length: {len(response.text)}")
        
        # Find championship/discipline names in HTML
        print("\n🔍 Searching for championship names...")
        
        # Look for <option> tags or discipline text
        import re
        options = re.findall(r'<option[^>]*>([^<]+)</option>', response.text)
        print(f"\n📋 Found {len(options)} <option> elements:")
        for opt in options[:20]:  # First 20
            print(f"  - {opt.strip()}")
        
        # Look for discipline/context text
        print("\n🔍 Searching for discipline/context patterns...")
        contexts = re.findall(r'(?:Discipline|Spécialité|Contexte)[^:]*:\s*([^<]+)', response.text, re.IGNORECASE)
        for ctx in contexts[:10]:
            print(f"  - {ctx.strip()}")
        
        # Save full HTML for inspection
        with open('/tmp/ctpb_debug.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"\n💾 Full HTML saved to: /tmp/ctpb_debug.html")

if __name__ == "__main__":
    asyncio.run(main())
